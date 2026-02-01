# RU Whitelist Routing

[![Build Status](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml/badge.svg)](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Автоматическая сборка `geoip.dat` и `geosite.dat` с дополнительными whitelist категориями для российских сервисов.

## 📦 Включенные категории

### geoip.dat
- **Все категории от [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip)**
- **WHITELIST** - IP-адреса российских сервисов из [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist)

### geosite.dat
- **Все категории от [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite)**
- **WHITELIST-RU** - Российские домены (VK, Ozon, Wildberries, Yandex и др.)
- **WHITELIST-ADS** - Рекламные домены

## 🔄 Обновления

Релизы создаются **автоматически каждые 3 дня** через GitHub Actions.

Формат версии: `YYYYMMDD` (например, `20260201`)

## 📥 Использование

### Скачивание

[Releases](../../releases/latest) → скачайте `geoip.dat` и `geosite.dat`

### Примеры конфигураций

#### Xray / V2Ray

```json
{
  "routing": {
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

#### Sing-box

```json
{
  "route": {
    "rules": [
      {
        "geoip": ["whitelist"],
        "outbound": "direct"
      },
      {
        "geosite": ["whitelist-ru", "whitelist-ads"],
        "outbound": "direct"
      }
    ]
  }
}
```

#### Clash Meta

```yaml
rules:
  - GEOIP,WHITELIST,DIRECT
  - GEOSITE,WHITELIST-RU,DIRECT
  - GEOSITE,WHITELIST-ADS,DIRECT
```

## 🛠️ Технические детали

Проект использует официальные инструменты:
- [v2fly/geoip](https://github.com/v2fly/geoip) - генератор geoip.dat
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) - генератор geosite.dat

## 🔗 Источники данных

- [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip)
- [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite)
- [kirilllavrov/RU-domain-list-for-whitelist](https://github.com/kirilllavrov/RU-domain-list-for-whitelist)

## 📝 Лицензия

MIT License
