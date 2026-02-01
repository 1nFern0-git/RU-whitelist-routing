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


def parse_ip_addresses(content):
    """
    Parse and validate IP addresses from content
    
    Args:
        content: Text content containing IP addresses
        
    Returns:
        List of valid IP addresses
    """
    ips = []
    
    # IP address pattern (simple validation)
    ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$')
    
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
    
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        
        # Remove 'domain:' prefix if present
        if line.startswith('domain:'):
            line = line[7:].strip()
        
        # Basic domain validation
        if line and '.' in line:
            domains.append(line)
    
    return domains


def main():
    """Main function"""
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config.json'
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"ERROR: Failed to load config.json: {e}", file=sys.stderr)
        return 1
    
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    
    whitelist_repo = config['sources']['whitelist']['repo']
    whitelist_branch = config['sources']['whitelist']['branch']
    
    # Process IP addresses from IPchecked directory
    print("\n=== Processing IP addresses ===", file=sys.stderr)
    ip_category = config['categories']['geoip'][0]
    ip_source_path = ip_category['source']
    
    ip_files = fetch_github_directory_files(whitelist_repo, ip_source_path, whitelist_branch)
    
    all_ips = []
    for filename in ip_files:
        file_path = f"{ip_source_path}/{filename}"
        print(f"Processing {file_path}...", file=sys.stderr)
        
        content = fetch_github_file_content(whitelist_repo, file_path, whitelist_branch)
        if content:
            ips = parse_ip_addresses(content)
            all_ips.extend(ips)
            print(f"  Found {len(ips)} IPs", file=sys.stderr)
    
    # Remove duplicates and sort
    all_ips = sorted(set(all_ips))
    
    # Save IP addresses
    ip_output = data_dir / 'whitelist_ips.txt'
    with open(ip_output, 'w') as f:
        f.write('\n'.join(all_ips))
    
    print(f"\nTotal IPs: {len(all_ips)}", file=sys.stderr)
    print(f"Saved to: {ip_output}", file=sys.stderr)
    
    # Process RU domains
    print("\n=== Processing RU domains ===", file=sys.stderr)
    ru_category = [cat for cat in config['categories']['geosite'] if cat['name'] == 'WHITELIST-RU'][0]
    ru_source_path = ru_category['source']
    
    ru_files = fetch_github_directory_files(whitelist_repo, ru_source_path, whitelist_branch)
    
    all_ru_domains = []
    for filename in ru_files:
        file_path = f"{ru_source_path}/{filename}"
        print(f"Processing {file_path}...", file=sys.stderr)
        
        content = fetch_github_file_content(whitelist_repo, file_path, whitelist_branch)
        if content:
            domains = parse_domains(content)
            all_ru_domains.extend(domains)
            print(f"  Found {len(domains)} domains", file=sys.stderr)
    
    # Remove duplicates and sort
    all_ru_domains = sorted(set(all_ru_domains))
    
    # Save RU domains
    ru_output = data_dir / 'whitelist_ru_domains.txt'
    with open(ru_output, 'w') as f:
        f.write('\n'.join(all_ru_domains))
    
    print(f"\nTotal RU domains: {len(all_ru_domains)}", file=sys.stderr)
    print(f"Saved to: {ru_output}", file=sys.stderr)
    
    # Process Ads domains
    print("\n=== Processing Ads domains ===", file=sys.stderr)
    ads_category = [cat for cat in config['categories']['geosite'] if cat['name'] == 'WHITELIST-ADS'][0]
    ads_source_path = ads_category['source']
    
    ads_files = fetch_github_directory_files(whitelist_repo, ads_source_path, whitelist_branch)
    
    all_ads_domains = []
    for filename in ads_files:
        file_path = f"{ads_source_path}/{filename}"
        print(f"Processing {file_path}...", file=sys.stderr)
        
        content = fetch_github_file_content(whitelist_repo, file_path, whitelist_branch)
        if content:
            domains = parse_domains(content)
            all_ads_domains.extend(domains)
            print(f"  Found {len(domains)} domains", file=sys.stderr)
    
    # Remove duplicates and sort
    all_ads_domains = sorted(set(all_ads_domains))
    
    # Save Ads domains
    ads_output = data_dir / 'whitelist_ads_domains.txt'
    with open(ads_output, 'w') as f:
        f.write('\n'.join(all_ads_domains))
    
    print(f"\nTotal Ads domains: {len(all_ads_domains)}", file=sys.stderr)
    print(f"Saved to: {ads_output}", file=sys.stderr)
    
    # Print summary
    print("\n=== Summary ===", file=sys.stderr)
    print(f"Total IPs: {len(all_ips)}", file=sys.stderr)
    print(f"Total RU domains: {len(all_ru_domains)}", file=sys.stderr)
    print(f"Total Ads domains: {len(all_ads_domains)}", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
