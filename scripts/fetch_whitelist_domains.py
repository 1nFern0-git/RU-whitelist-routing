#!/usr/bin/env python3
"""
Скачивание whitelist доменов из kirilllavrov/RU-domain-list-for-whitelist
"""
import os
import sys
import requests
from pathlib import Path

REPO = "kirilllavrov/RU-domain-list-for-whitelist"
BRANCH = "main"

def fetch_github_directory_files(repo: str, path: str, branch: str = "main") -> list[str]:
    """Получение списка файлов в директории GitHub"""
    try:
        api_url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        files = []
        for item in response.json():
            if item['type'] == 'file':
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

def parse_domains(content: str) -> set[str]:
    """Парсинг доменов из текста"""
    domains = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Убираем префиксы если есть
        domain = line.replace('domain:', '').replace('@ads', '').strip()
        
        # Базовая валидация домена
        if domain and '.' in domain and ' ' not in domain:
            domains.add(domain)
    
    return domains

def fetch_domains_from_directory(directory: str) -> set[str]:
    """Скачивание всех доменов из директории"""
    print(f"\n=== Processing {directory} ===")
    
    files = fetch_github_directory_files(REPO, directory, BRANCH)
    print(f"Found {len(files)} files")
    
    all_domains = set()
    for filename in files:
        print(f"Processing: {filename}")
        content = fetch_github_file_content(REPO, f"{directory}/{filename}", BRANCH)
        if content:
            domains = parse_domains(content)
            all_domains.update(domains)
            print(f"  → {len(domains)} domains")
    
    return all_domains

def save_domains_v2fly_format(domains: set[str], output_file: Path, category_name: str):
    """Сохранение доменов в формате v2fly domain-list-community"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # Добавляем комментарий с названием категории
        f.write(f"# {category_name}\n")
        f.write(f"# Total domains: {len(domains)}\n\n")
        
        # Записываем домены в формате v2fly
        for domain in sorted(domains):
            f.write(f"domain:{domain}\n")

def main():
    """Основная функция"""
    print("=== Fetching Whitelist Domains ===")
    
    # Создание директории для данных
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # === Российские домены ===
    ru_domains = fetch_domains_from_directory("domains/ru")
    print(f"\n✓ Total RU domains: {len(ru_domains)}")
    
    ru_output = data_dir / "whitelist-ru"
    save_domains_v2fly_format(ru_domains, ru_output, "WHITELIST-RU")
    print(f"✓ Saved to: {ru_output}")
    
    # === Рекламные домены ===
    ads_domains = fetch_domains_from_directory("domains/ads")
    print(f"\n✓ Total ADS domains: {len(ads_domains)}")
    
    ads_output = data_dir / "whitelist-ads"
    save_domains_v2fly_format(ads_domains, ads_output, "WHITELIST-ADS")
    print(f"✓ Saved to: {ads_output}")
    
    # === Статистика ===
    print("\n=== Summary ===")
    print(f"RU domains:  {len(ru_domains):>6}")
    print(f"ADS domains: {len(ads_domains):>6}")

if __name__ == "__main__":
    main()
