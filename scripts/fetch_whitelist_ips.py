#!/usr/bin/env python3
"""
Скачивание whitelist IP-адресов из kirilllavrov/RU-domain-list-for-whitelist
"""
import os
import sys
import requests
from pathlib import Path

REPO = "kirilllavrov/RU-domain-list-for-whitelist"
BRANCH = "main"
IP_DIR = "IPchecked"

def fetch_github_directory_files(repo: str, path: str, branch: str = "main") -> list[str]:
    """Получение списка файлов в директории GitHub"""
    try:
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        files = []
        for item in response.json():
            if item['type'] == 'file' and item['name'].endswith('.txt'):
                files.append(item['name'])
        
        return files
    except Exception as e:
        print(f"✗ Error listing directory {path}: {e}", file=sys.stderr)
        return []

def fetch_github_file_content(repo: str, path: str, branch: str = "main") -> str:
    """Получение содержимого файла из GitHub"""
    try:
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"✗ Error fetching {path}: {e}", file=sys.stderr)
        return ""

def parse_ips(content: str) -> set[str]:
    """Парсинг IP-адресов из текста"""
    ips = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Проверка формата IP или CIDR
        if '/' in line:
            # CIDR формат
            parts = line.split('/')
            if len(parts) == 2:
                ip_parts = parts[0].split('.')
                if len(ip_parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in ip_parts):
                    ips.add(line)
        else:
            # Обычный IP
            parts = line.split('.')
            if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                ips.add(line)
    
    return ips

def main():
    """Основная функция"""
    print("=== Fetching Whitelist IPs ===")
    
    # Создание директории для данных
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Получение списка файлов
    ip_files = fetch_github_directory_files(REPO, IP_DIR, BRANCH)
    print(f"Found {len(ip_files)} IP files")
    
    if not ip_files:
        print("✗ No IP files found!", file=sys.stderr)
        sys.exit(1)
    
    # Сбор всех IP
    all_ips = set()
    for filename in ip_files:
        print(f"Processing: {filename}")
        content = fetch_github_file_content(REPO, f"{IP_DIR}/{filename}", BRANCH)
        if content:
            ips = parse_ips(content)
            all_ips.update(ips)
            print(f"  → {len(ips)} IPs/CIDRs")
    
    print(f"\n✓ Total unique IPs/CIDRs: {len(all_ips)}")
    
    # Сохранение в файл
    output_file = data_dir / "whitelist-ips.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for ip in sorted(all_ips):
            f.write(f"{ip}\n")
    
    print(f"✓ Saved to: {output_file}")

if __name__ == "__main__":
    main()
