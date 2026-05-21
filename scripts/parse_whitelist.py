#!/usr/bin/env python3
"""
parse_whitelist.py - Parse whitelist data from GitHub repository
"""
import sys
import os
import json
import re
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
    Parse and validate IP addresses from content
    
    Args:
        content: Text content containing IP addresses
        
    Returns:
        List of valid IP addresses
    """
    ips = []
    
    # IP address pattern with proper octet validation (0-255)
    ip_pattern = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        r'(?:/(?:3[0-2]|[1-2]?[0-9]))?$'
    )
    
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        # Validate IP format
        if ip_pattern.match(line):
            ips.append(line)
    
    return ips


def parse_domains(content):
    """
    Parse domains from content, removing 'domain:' prefix if present
    
    Args:
        content: Text content containing domains
        
    Returns:
        List of domain names
    """
    domains = []
    
    # Domain validation pattern (basic but proper)
    # Allows letters, numbers, hyphens, and dots
    # Must start with alphanumeric, end with alphanumeric
    # Must have at least one dot
    domain_pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        # Remove 'domain:' prefix if present
        if line.startswith('domain:'):
            line = line[7:].strip()
        
        # Validate domain format
        if line and domain_pattern.match(line):
            domains.append(line)
    
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

    # Process IP addresses (WHITELIST)
    print("\n=== Processing IP addresses ===", file=sys.stderr)
    ip_category = find_category('geoip', 'WHITELIST')
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
