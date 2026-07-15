#!/usr/bin/env python3
"""
build_geosite_data.py - Assemble the geosite source tree for the v2fly builder.

Replaces the old binary-append merge_geosite.py. Instead of patching a prebuilt
geosite.dat, we rebuild it from sources:

  1. Fetch the upstream data/ category files (dlc text format) from
     config.sources.geosite_data.
  2. Generate the whitelist-ru category from data/whitelist_ru_domains.txt.
  3. Apply custom/geosite/include and custom/geosite/exclude overlays per
     category (text-level; the upstream files use no include: directives or
     @attributes, so exact-rule add/remove is sufficient and complete).
  4. Write the resulting tree to downloads/geosite-data/, which CI copies into
     the v2fly/domain-list-community builder's data/ directory.
"""
import sys
import time
import json
import shutil
from pathlib import Path

from parse_whitelist import (
    fetch_github_directory_files, fetch_github_file_content, normalize_domain,
)
from overlay_common import (
    warn, fail, append_step_summary, load_overlay_entries, Counters,
)


def fetch_with_retry(repo, path, branch, attempts=4, delay=2):
    """Fetch a raw file, retrying transient network/SSL failures."""
    for attempt in range(1, attempts + 1):
        content = fetch_github_file_content(repo, path, branch)
        if content is not None:
            return content
        if attempt < attempts:
            warn(f"retry {attempt}/{attempts - 1} fetching {path}")
            time.sleep(delay * attempt)
    return None


def parse_rule(text):
    """
    Parse one dlc-format line into a (type, value) rule, or None if invalid.

    type is one of: 'domain' (RootDomain), 'full' (exact), 'keyword' (Plain),
    'regexp' (Regex). A bare line with no prefix is treated as 'domain'.
    Domains are normalized to punycode; keyword/regexp values are left as-is
    (keyword lowercased for stable matching).
    """
    text = text.strip()
    if not text:
        return None

    if text.startswith('full:'):
        dom = normalize_domain(text[5:])
        return ('full', dom) if dom else None
    if text.startswith('domain:'):
        dom = normalize_domain(text[7:])
        return ('domain', dom) if dom else None
    if text.startswith('keyword:'):
        val = text[8:].strip().lower()
        return ('keyword', val) if val else None
    if text.startswith('regexp:'):
        val = text[7:].strip()
        return ('regexp', val) if val else None

    dom = normalize_domain(text)
    return ('domain', dom) if dom else None


def render_rule(rule):
    """Render a (type, value) rule back to canonical dlc text."""
    return f"{rule[0]}:{rule[1]}"


def load_source_categories(config, base_dir):
    """
    Fetch upstream category files. Returns {category: [raw_line, ...]}.
    Category name == filename (lowercased).
    """
    src = config['sources']['geosite_data']
    repo = src['repo']
    branch = src.get('branch', 'master')
    path = src['path']

    filenames = fetch_github_directory_files(repo, path, branch)
    if not filenames:
        fail(f"no source files found at {repo}:{path}@{branch}")

    categories = {}
    for name in filenames:
        content = fetch_with_retry(repo, f"{path}/{name}", branch)
        if content is None:
            fail(f"failed to fetch {repo}:{path}/{name}")
        categories[name.lower()] = content.splitlines()
    print(f"Fetched {len(categories)} upstream categories", file=sys.stderr)
    return categories


def build_whitelist_ru_lines(base_dir):
    """Build the whitelist-ru category lines from parsed whitelist domains."""
    domains_file = base_dir / 'data' / 'whitelist_ru_domains.txt'
    if not domains_file.exists():
        fail(f"{domains_file} not found (run parse_whitelist.py first)")

    lines = []
    for raw in domains_file.read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        # parse_whitelist emits either 'full:domain' or a bare domain.
        rule = parse_rule(raw)
        if rule:
            lines.append(render_rule(rule))
    return lines


def existing_rules(lines):
    """Set of (type, value) rules present among non-comment lines."""
    rules = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        rule = parse_rule(stripped)
        if rule:
            rules.add(rule)
    return rules


def apply_geosite_overlays(category, lines, overlay_dir, counters, unmatched_report):
    """
    Apply include/exclude overlays to one category's lines. Returns new lines.
    """
    includes = load_overlay_entries(overlay_dir, 'include', category)
    excludes = load_overlay_entries(overlay_dir, 'exclude', category)
    if not includes and not excludes:
        return lines

    inc_rules = {}
    for lineno, text in includes:
        rule = parse_rule(text)
        if rule is None:
            fail(f"custom/geosite/include/{category}.txt:{lineno}: invalid rule '{text}'")
        inc_rules.setdefault(rule, lineno)

    exc_rules = {}
    for lineno, text in excludes:
        rule = parse_rule(text)
        if rule is None:
            fail(f"custom/geosite/exclude/{category}.txt:{lineno}: invalid rule '{text}'")
        exc_rules.setdefault(rule, lineno)

    conflict = set(inc_rules) & set(exc_rules)
    if conflict:
        listed = ', '.join(render_rule(r) for r in sorted(conflict))
        fail(f"geosite category '{category}': {listed} appear in both include and exclude")

    # Excludes: drop lines whose rule matches; track which excludes matched.
    matched_exc = set()
    kept = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            rule = parse_rule(stripped)
            if rule in exc_rules:
                matched_exc.add(rule)
                counters.removed += 1
                continue
        kept.append(line)

    for rule in exc_rules:
        if rule not in matched_exc:
            counters.unmatched += 1
            warn(f"geosite exclude {render_rule(rule)} matched nothing in '{category}' (stale?)")
            unmatched_report.append(
                f"- `geosite:{category}` exclude `{render_rule(rule)}` — no match")

    # Includes: append canonical lines not already present.
    present = existing_rules(kept)
    additions = []
    for rule in inc_rules:
        if rule in present:
            warn(f"geosite include {render_rule(rule)} already in '{category}'; skipping")
            counters.skipped_dup += 1
        else:
            additions.append(render_rule(rule))
            present.add(rule)
            counters.added += 1

    if additions:
        kept.append(f"# --- custom includes ({category}) ---")
        kept.extend(additions)
    return kept


def main():
    base_dir = Path(__file__).parent.parent
    config = json.loads((base_dir / 'config.json').read_text(encoding='utf-8'))
    overlay_dir = base_dir / 'custom' / 'geosite'

    staging = base_dir / 'downloads' / 'geosite-data'
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    categories = load_source_categories(config, base_dir)
    categories['whitelist-ru'] = build_whitelist_ru_lines(base_dir)
    print(f"Generated whitelist-ru: {len(categories['whitelist-ru'])} rules",
          file=sys.stderr)

    # Categories that exist only as an include overlay (brand-new categories).
    for kind_dir in [overlay_dir / 'include']:
        for f in kind_dir.glob('*.txt'):
            cat = f.stem
            if cat not in categories and load_overlay_entries(overlay_dir, 'include', cat):
                categories[cat] = []
                warn(f"creating new geosite category '{cat}' from include overlay only")

    print("Applying geosite overlays...", file=sys.stderr)
    unmatched_report = []
    for category in sorted(categories):
        counters = Counters()
        categories[category] = apply_geosite_overlays(
            category, categories[category], overlay_dir, counters, unmatched_report)
        if counters.nonzero():
            print(counters.report_line(category), file=sys.stderr)

        content = '\n'.join(categories[category])
        if content and not content.endswith('\n'):
            content += '\n'
        # newline='' keeps LF verbatim (no CRLF translation on Windows), so the
        # staged tree is byte-identical on every platform / in CI.
        (staging / category).write_text(content, encoding='utf-8', newline='')

    print(f"Wrote {len(categories)} category files to {staging}", file=sys.stderr)

    if unmatched_report:
        append_step_summary(["### geosite: unmatched excludes", *unmatched_report])

    return 0


if __name__ == '__main__':
    sys.exit(main())
