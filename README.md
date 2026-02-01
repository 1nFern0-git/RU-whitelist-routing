# RU Whitelist Routing

[![Build Status](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml/badge.svg)](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Автоматическая сборка `geoip.dat` и `geosite.dat` с whitelist категориями из российских источников для Xray, V2Ray, Sing-box и Clash Meta. Обновление каждые 3 дня.

## Категории

- **WHITELIST** (GeoIP) - IP адреса из российских источников
- **WHITELIST-RU** (GeoSite) - Российские домены
- **WHITELIST-ADS** (GeoSite) - Рекламные домены

Скачать: [Releases](https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest)

## Использование

### Xray / V2Ray

```json
{
  "routing": {
    "rules": [
      {"type": "field", "ip": ["geoip:WHITELIST"], "outboundTag": "direct"},
      {"type": "field", "domain": ["geosite:WHITELIST-RU", "geosite:WHITELIST-ADS"], "outboundTag": "direct"}
    ]
  }
}
```

### Sing-box

```json
{
  "route": {
    "rules": [
      {"geoip": "WHITELIST", "outbound": "direct"},
      {"geosite": ["WHITELIST-RU", "WHITELIST-ADS"], "outbound": "direct"}
    ]
  }
}
```

### Clash Meta

```yaml
rules:
  - GEOIP,WHITELIST,DIRECT
  - GEOSITE,WHITELIST-RU,DIRECT
  - GEOSITE,WHITELIST-ADS,DIRECT
```

## Локальная сборка

```bash
pip install -r requirements.txt
python scripts/fetch_sources.py
python scripts/parse_whitelist.py
python scripts/merge_geoip.py
python scripts/merge_geosite.py
```

Результаты в `output/geoip.dat` и `output/geosite.dat`.

## Источники

- [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) - базовый GeoIP файл
- [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) - базовый GeoSite файл
- [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist) - whitelist данные

## Лицензия

[MIT License](LICENSE)
