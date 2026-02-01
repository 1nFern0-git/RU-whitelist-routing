#!/usr/bin/env python3
"""
fetch_sources.py - Download source files from GitHub releases
"""
import sys
import os
import json
import requests
from pathlib import Path


def get_latest_release_asset(repo, asset_name):
    """
    Get download URL for an asset from the latest release
    
    Args:
        repo: Repository name (owner/repo)
        asset_name: Name of the asset to download
        
    Returns:
        URL of the asset or None if not found
    """
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    
    try:
        print(f"Fetching latest release from {repo}...", file=sys.stderr)
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        release_data = response.json()
        
        for asset in release_data.get('assets', []):
            if asset['name'] == asset_name:
                print(f"Found asset: {asset_name}", file=sys.stderr)
                return asset['browser_download_url']
        
        print(f"ERROR: Asset {asset_name} not found in latest release", file=sys.stderr)
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch release info: {e}", file=sys.stderr)
        return None


def download_file(url, destination):
    """
    Download a file with progress indication
    
    Args:
        url: URL to download from
        destination: Path where to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Downloading {url}...", file=sys.stderr)
        
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rProgress: {progress:.1f}%", end='', file=sys.stderr)
        
        if total_size > 0:
            print(file=sys.stderr)  # New line after progress
        
        print(f"Downloaded: {destination} ({downloaded} bytes)", file=sys.stderr)
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to download file: {e}", file=sys.stderr)
        return False
    except IOError as e:
        print(f"ERROR: Failed to write file: {e}", file=sys.stderr)
        return False


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
    
    downloads_dir = Path(__file__).parent.parent / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    # Download geoip.dat
    geoip_config = config['sources']['geoip']
    geoip_url = get_latest_release_asset(geoip_config['repo'], geoip_config['asset'])
    
    if not geoip_url:
        print("ERROR: Failed to get geoip.dat URL", file=sys.stderr)
        return 1
    
    if not download_file(geoip_url, downloads_dir / 'geoip.dat'):
        print("ERROR: Failed to download geoip.dat", file=sys.stderr)
        return 1
    
    # Download geosite.dat
    geosite_config = config['sources']['geosite']
    geosite_url = get_latest_release_asset(geosite_config['repo'], geosite_config['asset'])
    
    if not geosite_url:
        print("ERROR: Failed to get geosite.dat URL", file=sys.stderr)
        return 1
    
    if not download_file(geosite_url, downloads_dir / 'geosite.dat'):
        print("ERROR: Failed to download geosite.dat", file=sys.stderr)
        return 1
    
    print("\nAll source files downloaded successfully!", file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
