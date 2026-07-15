#!/usr/bin/env python3
"""
validate_build.py - Post-build invariant checks. A failure here means the job
fails and no release is published, so users stay on the previous release.

Invariants:
  1. Every category in output/{geoip,geosite}.dat is non-empty.
  2. Every category referenced by JSON.DEFAULT exists in the matching file.
  3. Versus the previous release (if available): no category disappeared, and
     no sizeable category dropped more than the allowed percentage of entries.
"""
import os
import sys
import json
import re
from pathlib import Path

from patch_geoip import iter_fields, decode_geoip


def decode_geoip_counts(data):
    return {e['cc'].upper(): len(e['nets']) for e in decode_geoip(data)}


def decode_geosite_counts(data):
    counts = {}
    for field, wire, val, _ in iter_fields(data):
        if field == 1 and wire == 2:
            cc = None
            n = 0
            for f2, w2, v2, _ in iter_fields(val):
                if f2 == 1 and w2 == 2:
                    cc = v2.decode('utf-8')
                elif f2 == 2 and w2 == 2:
                    n += 1
            if cc is not None:
                counts[cc.upper()] = n
    return counts


def referenced_categories(json_default):
    """Return (geoip_names, geosite_names) referenced by the routing template."""
    data = json.loads(Path(json_default).read_text(encoding='utf-8'))
    geoip, geosite = set(), set()
    for key in ('DirectSites', 'ProxySites', 'BlockSites',
                'DirectIp', 'ProxyIp', 'BlockIp'):
        for ref in data.get(key, []):
            m = re.match(r'^(geoip|geosite):(.+)$', ref.strip(), re.IGNORECASE)
            if not m:
                continue
            if m.group(1).lower() == 'geoip':
                geoip.add(m.group(2).upper())
            else:
                geosite.add(m.group(2).upper())
    return geoip, geosite


def check_nonempty(kind, counts, errors):
    for cat, n in sorted(counts.items()):
        if n == 0:
            errors.append(f"{kind}: category '{cat}' is empty")


def check_referenced(kind, refs, counts, errors):
    for cat in sorted(refs):
        if cat not in counts:
            errors.append(f"{kind}: JSON.DEFAULT references '{cat}' but it is missing")
        elif counts[cat] == 0:
            errors.append(f"{kind}: JSON.DEFAULT references '{cat}' but it is empty")


def check_drop(kind, prev, new, min_count, max_drop_pct, errors):
    if prev is None:
        print(f"  {kind}: no previous release to compare against", file=sys.stderr)
        return
    for cat, old_n in sorted(prev.items()):
        new_n = new.get(cat)
        if new_n is None:
            errors.append(f"{kind}: category '{cat}' present in previous release but gone now")
            continue
        if old_n >= min_count:
            floor = old_n * (1 - max_drop_pct / 100.0)
            if new_n < floor:
                pct = 100.0 * (old_n - new_n) / old_n
                errors.append(
                    f"{kind}: category '{cat}' dropped {pct:.1f}% "
                    f"({old_n} -> {new_n}, max {max_drop_pct}%)")


def load_counts(path, decoder):
    p = Path(path)
    if not p.exists():
        return None
    return decoder(p.read_bytes())


def main():
    base_dir = Path(__file__).parent.parent
    config = json.loads((base_dir / 'config.json').read_text(encoding='utf-8'))
    vcfg = config.get('validation', {})
    min_count = vcfg.get('min_count_for_drop_check', 50)
    max_drop_pct = vcfg.get('max_category_drop_pct', 20)

    geoip_out = base_dir / 'output' / 'geoip.dat'
    geosite_out = base_dir / 'output' / 'geosite.dat'
    if not geoip_out.exists() or not geosite_out.exists():
        print("ERROR: output/geoip.dat or output/geosite.dat missing", file=sys.stderr)
        return 1

    new_geoip = decode_geoip_counts(geoip_out.read_bytes())
    new_geosite = decode_geosite_counts(geosite_out.read_bytes())
    print(f"geoip categories:   {len(new_geoip)}", file=sys.stderr)
    print(f"geosite categories: {len(new_geosite)}", file=sys.stderr)

    prev_dir = os.environ.get('PREV_RELEASE_DIR', '/tmp/prev_release')
    prev_geoip = load_counts(Path(prev_dir) / 'geoip.dat', decode_geoip_counts)
    prev_geosite = load_counts(Path(prev_dir) / 'geosite.dat', decode_geosite_counts)

    ref_geoip, ref_geosite = referenced_categories(base_dir / 'JSON.DEFAULT')

    errors = []
    check_nonempty('geoip', new_geoip, errors)
    check_nonempty('geosite', new_geosite, errors)
    check_referenced('geoip', ref_geoip, new_geoip, errors)
    check_referenced('geosite', ref_geosite, new_geosite, errors)
    check_drop('geoip', prev_geoip, new_geoip, min_count, max_drop_pct, errors)
    check_drop('geosite', prev_geosite, new_geosite, min_count, max_drop_pct, errors)

    if errors:
        print("\nVALIDATION FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("\nAll post-build invariants passed.", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
