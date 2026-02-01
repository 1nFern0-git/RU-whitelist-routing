# RU Whitelist Routing

[![Build Status](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml/badge.svg)](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Автоматическая сборка `geoip.dat` и `geosite.dat` с дополнительными whitelist категориями из российских источников для маршрутизации трафика в Xray, V2Ray, Sing-box и Clash Meta.

## Описание

Этот проект автоматически собирает и объединяет данные из нескольких источников для создания файлов маршрутизации с российскими whitelist категориями:

- **WHITELIST** - IP адреса из российских источников
- **WHITELIST-RU** - Российские домены
- **WHITELIST-ADS** - Рекламные домены

Файлы обновляются автоматически каждые 3 дня с помощью GitHub Actions.

## Категории

### GeoIP

| Категория | Описание | Источник |
|-----------|----------|----------|
| **WHITELIST** | IP адреса из российских источников | [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) (IPchecked) |

### GeoSite

| Категория | Описание | Источник |
|-----------|----------|----------|
| **WHITELIST-RU** | Российские домены | [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) (domains/ru) |
| **WHITELIST-ADS** | Рекламные домены | [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) (domains/ads) |

## Обновления

- Автоматическая сборка: **каждые 3 дня**
- Формат тега релиза: `YYYYMMDD` (например, `20260201`)
- Последний релиз доступен в [Releases](https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest)

## Использование

### Скачивание файлов

Последние версии файлов доступны в [Releases](https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest):

- `geoip.dat` - файл с IP категориями
- `geosite.dat` - файл с доменными категориями

### Xray / V2Ray

Добавьте правила маршрутизации в конфигурацию:

```json
{
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "ip": ["geoip:whitelist"],
        "outboundTag": "direct"
      },
      {
        "type": "field",
        "domain": ["geosite:whitelist-ru", "geosite:whitelist-ads"],
        "outboundTag": "direct"
      }
    ]
  }
}
```

Замените `geoip.dat` и `geosite.dat` в директории с конфигурацией Xray/V2Ray.

### Sing-box

```json
{
  "route": {
    "rules": [
      {
        "geoip": "whitelist",
        "outbound": "direct"
      },
      {
        "geosite": ["whitelist-ru", "whitelist-ads"],
        "outbound": "direct"
      }
    ],
    "geoip": {
      "path": "geoip.dat"
    },
    "geosite": {
      "path": "geosite.dat"
    }
  }
}
```

### Clash Meta

```yaml
geodata-mode: true
geox-url:
  geoip: "https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest/download/geoip.dat"
  geosite: "https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest/download/geosite.dat"

rules:
  - GEOIP,WHITELIST,DIRECT
  - GEOSITE,WHITELIST-RU,DIRECT
  - GEOSITE,WHITELIST-ADS,DIRECT
```

## Локальная сборка

### Требования

- Python 3.11+
- Git

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Запуск сборки

```bash
# 1. Скачать исходные файлы
python scripts/fetch_sources.py

# 2. Распарсить whitelist данные
python scripts/parse_whitelist.py

# 3. Собрать geoip.dat
python scripts/merge_geoip.py

# 4. Собрать geosite.dat
python scripts/merge_geosite.py
```

Результаты будут в директории `output/`:
- `output/geoip.dat`
- `output/geosite.dat`

## Структура проекта

```
.
├── .github/
│   └── workflows/
│       └── build.yml          # GitHub Actions workflow
├── scripts/
│   ├── fetch_sources.py       # Скачивание источников
│   ├── parse_whitelist.py     # Парсинг whitelist данных
│   ├── merge_geoip.py         # Добавление категорий в geoip.dat
│   └── merge_geosite.py       # Добавление категорий в geosite.dat
├── config.json                # Конфигурация источников
├── requirements.txt           # Python зависимости
├── README.md                  # Документация
├── LICENSE                    # MIT License
└── .gitignore                 # Git ignore файл
```

## Источники данных

Проект использует следующие источники:

- **GeoIP базовый файл**: [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip)
  - Базовый файл с IP категориями
  
- **GeoSite базовый файл**: [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite)
  - Базовый файл с доменными категориями
  
- **Whitelist данные**: [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist)
  - IP адреса (IPchecked)
  - Российские домены (domains/ru)
  - Рекламные домены (domains/ads)

## Технические детали

### Формат файлов

Используется формат V2Ray GeoIP/GeoSite на основе Protocol Buffers:

- **GeoIP**: `country_code` (string) + repeated `CIDR` (ip bytes + prefix uint32)
- **GeoSite**: `country_code` (string) + repeated `Domain` (type enum + value string)
- Domain type = 2 (Domain - включает поддомены)

### Workflow

GitHub Actions workflow автоматически:

1. Скачивает последние версии базовых файлов из релизов
2. Получает актуальные whitelist данные из исходного репозитория
3. Парсит и валидирует IP адреса и домены
4. Создает новые категории в protobuf формате
5. Добавляет категории к базовым файлам
6. Создает релиз с обновленными файлами

## Благодарности

Огромная благодарность авторам и контрибьюторам проектов:

- [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) - за базовый GeoIP файл
- [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) - за базовый GeoSite файл
- [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) - за актуальные whitelist данные
- Сообществу Xray, V2Ray, Sing-box и Clash за разработку и поддержку инструментов

## Лицензия

Проект распространяется под лицензией [MIT License](LICENSE).

## Поддержка

Если у вас возникли проблемы или есть предложения:

- Создайте [Issue](https://github.com/1nFern0-git/RU-whitelist-routing/issues)
- Отправьте Pull Request с улучшениями

---

**Примечание**: Этот проект предназначен только для образовательных целей. Используйте на свой страх и риск.
