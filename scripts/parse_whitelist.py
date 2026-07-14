#!/usr/bin/env python3
"""
parse_whitelist.py - Parse whitelist data from GitHub repository
"""
import sys
import os
import json
import re
import ipaddress
import requests
from pathlib import Path


def fetch_github_file_content(repo, path, branch='main'):
    """
    Get raw content of a file from GitHub
    
    Args:
        repo: Repository name (owner/repo)
        path: Path to file in repository
        branch: Branch name (default: main)
        
    Returns:
        File content as string or None if failed
    """
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    
    # Use GitHub token if available for API calls
    headers = {}
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        response = requests.get(raw_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch {path}: {e}", file=sys.stderr)
        return None


def fetch_github_directory_files(repo, path, branch='main'):
    """
    Get list of files in a directory via GitHub API
    
    Args:
        repo: Repository name (owner/repo)
        path: Path to directory in repository
        branch: Branch name (default: main)
        
    Returns:
        List of file names or empty list if failed
    """
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    
    # Use GitHub token if available
    headers = {}
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        print(f"Fetching file list from {path}...", file=sys.stderr)
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        contents = response.json()
        
        # Filter only files (not directories)
        files = [item['name'] for item in contents if item['type'] == 'file']
        print(f"Found {len(files)} files in {path}", file=sys.stderr)
        return files
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch directory listing: {e}", file=sys.stderr)
        return []


def category_repo(category, default_repo, default_branch):
    """Resolve the (repo, branch) pair for a category, falling back to defaults."""
    return category.get('repo', default_repo), category.get('branch', default_branch)


def collect_category_contents(category, default_repo, default_branch):
    """
    Fetch raw text content(s) for a category. Supports two modes:
    - 'file': single file at category['file']
    - 'source': directory listing; fetches every file inside category['source']
    """
    repo, branch = category_repo(category, default_repo, default_branch)

    if 'file' in category:
        file_path = category['file']
        print(f"Processing {repo}:{file_path}...", file=sys.stderr)
        content = fetch_github_file_content(repo, file_path, branch)
        return [content] if content else []

    if 'source' in category:
        dir_path = category['source']
        filenames = fetch_github_directory_files(repo, dir_path, branch)
        contents = []
        for filename in filenames:
            file_path = f"{dir_path}/{filename}"
            print(f"Processing {file_path}...", file=sys.stderr)
            content = fetch_github_file_content(repo, file_path, branch)
            if content:
                contents.append(content)
        return contents

    raise ValueError(f"Category {category.get('name')!r} has neither 'file' nor 'source'")


def parse_ip_addresses(content):
    """
    Parse and validate IP addresses from content (IPv4 and IPv6)

    Accepts single addresses ("1.2.3.4", "2001:db8::1") and CIDR ranges
    ("1.2.3.0/24", "2001:db8::/32"). Validation is delegated to the
    stdlib ``ipaddress`` module so both families are handled uniformly.

    Args:
        content: Text content containing IP addresses

    Returns:
        List of valid IP address / CIDR strings (original textual form)
    """
    ips = []

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            continue

        try:
            if '/' in line:
                ipaddress.ip_network(line, strict=False)
            else:
                ipaddress.ip_address(line)
        except ValueError:
            continue

        ips.append(line)

    return ips


# Validation pattern applied to the ASCII/punycode form of a domain.
# The TLD label may be an ACE ("xn--") label, so digits and hyphens are
# permitted there as well - Cyrillic zones like .рф become .xn--p1ai.
_ASCII_DOMAIN_RE = re.compile(
    r'^(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z0-9\-]{2,}$'
)


def normalize_domain(name):
    """
    Normalize a domain to its ASCII/punycode (IDNA) form.

    Internationalized domains (e.g. 'мвд.рф') are converted to their ACE
    representation ('xn--b1aew.xn--p1ai') so they match how clients send
    the SNI/DNS name on the wire and how canonical geosite.dat files store
    them. Returns None if the value is not a valid hostname.

    Args:
        name: Raw domain string (may contain non-ASCII characters)

    Returns:
        ASCII/punycode domain string, or None if invalid
    """
    name = name.strip().rstrip('.').lower()
    if not name:
        return None

    try:
        # The stdlib 'idna' codec performs ToASCII per label. Already-ASCII
        # (incl. existing 'xn--') labels pass through unchanged.
        ascii_name = name.encode('idna').decode('ascii')
    except (UnicodeError, ValueError):
        # idna rejects some otherwise-valid ASCII hostnames (e.g. numeric
        # labels); keep those, but drop anything still non-ASCII.
        try:
            name.encode('ascii')
        except UnicodeEncodeError:
            return None
        ascii_name = name

    return ascii_name if _ASCII_DOMAIN_RE.match(ascii_name) else None


def parse_domains(content):
    """
    Parse domains from content, removing 'domain:' prefix if present.

    A 'full:' prefix (exact match, no subdomains) is preserved in the
    output so downstream (merge_geosite.py) can pick the right Domain
    Rule type. Internationalized domains are converted to punycode via
    normalize_domain().

    Args:
        content: Text content containing domains

    Returns:
        List of domain names (optionally prefixed with 'full:')
    """
    domains = []

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            continue

        # Remove 'domain:'/'full:' prefix if present, keeping track of it
        prefix = ''
        if line.startswith('domain:'):
            line = line[7:].strip()
        elif line.startswith('full:'):
            prefix = 'full:'
            line = line[5:].strip()

        ascii_domain = normalize_domain(line)
        if ascii_domain:
            domains.append(prefix + ascii_domain)

    return domains


def main():
    """Main function"""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"ERROR: Failed to load config.json: {e}", file=sys.stderr)
        return 1
    
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    default_repo = config['sources']['whitelist']['repo']
    default_branch = config['sources']['whitelist']['branch']

    def find_category(group, name):
        matches = [cat for cat in config['categories'][group] if cat['name'] == name]
        if not matches:
            raise KeyError(f"{name} category not found in config['categories'][{group!r}]")
        return matches[0]

    # Process IP addresses (WHITELIST-RU)
    print("\n=== Processing IP addresses ===", file=sys.stderr)
    ip_category = find_category('geoip', 'WHITELIST-RU')
    all_ips = []
    for content in collect_category_contents(ip_category, default_repo, default_branch):
        ips = parse_ip_addresses(content)
        all_ips.extend(ips)
        print(f"  Found {len(ips)} IPs", file=sys.stderr)
    all_ips = sorted(set(all_ips))

    ip_output = data_dir / 'whitelist_ips.txt'
    with open(ip_output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_ips))
    print(f"\nTotal IPs: {len(all_ips)}", file=sys.stderr)
    print(f"Saved to: {ip_output}", file=sys.stderr)

    # Process RU domains (WHITELIST-RU)
    print("\n=== Processing RU domains ===", file=sys.stderr)
    ru_category = find_category('geosite', 'WHITELIST-RU')
    all_ru_domains = []
    for content in collect_category_contents(ru_category, default_repo, default_branch):
        domains = parse_domains(content)
        all_ru_domains.extend(domains)
        print(f"  Found {len(domains)} domains", file=sys.stderr)
    all_ru_domains = sorted(set(all_ru_domains))

    ru_output = data_dir / 'whitelist_ru_domains.txt'
    with open(ru_output, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_ru_domains))
    print(f"\nTotal RU domains: {len(all_ru_domains)}", file=sys.stderr)
    print(f"Saved to: {ru_output}", file=sys.stderr)

    # Print summary
    print("\n=== Summary ===", file=sys.stderr)
    print(f"Total IPs: {len(all_ips)}", file=sys.stderr)
    print(f"Total RU domains: {len(all_ru_domains)}", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
