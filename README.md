# RU Whitelist Routing

[![Build Status](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml/badge.svg)](https://github.com/1nFern0-git/RU-whitelist-routing/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Автоматическая сборка `geoip.dat` и `geosite.dat` с whitelist категориями из российских источников для Xray, V2Ray, Sing-box и Clash Meta. Обновление каждые 3 дня.

## Категории

- **WHITELIST-RU** (GeoIP) - IP адреса из российских источников
- **WHITELIST-RU** (GeoSite) - Российские домены

Скачать Latest файлы:

**GitHub Releases:**  
[geoip.dat](https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest/download/geoip.dat)  
[geosite.dat](https://github.com/1nFern0-git/RU-whitelist-routing/releases/latest/download/geosite.dat)

**jsDelivr CDN** (зеркало, может быть быстрее в РФ):  
[geoip.dat](https://cdn.jsdelivr.net/gh/1nFern0-git/RU-whitelist-routing@release/geoip.dat)  
[geosite.dat](https://cdn.jsdelivr.net/gh/1nFern0-git/RU-whitelist-routing@release/geosite.dat)

**GitHub raw** (ветка `release`):  
[geoip.dat](https://raw.githubusercontent.com/1nFern0-git/RU-whitelist-routing/release/geoip.dat)  
[geosite.dat](https://raw.githubusercontent.com/1nFern0-git/RU-whitelist-routing/release/geosite.dat)

## Использование

### Xray / V2Ray

```json
{
  "routing": {
    "rules": [
      {"type": "field", "ip": ["geoip:WHITELIST-RU"], "outboundTag": "direct"},
      {"type": "field", "domain": ["geosite:WHITELIST-RU"], "outboundTag": "direct"}
    ]
  }
}
```

### Sing-box

```json
{
  "route": {
    "rules": [
      {"geoip": "WHITELIST-RU", "outbound": "direct"},
      {"geosite": ["WHITELIST-RU"], "outbound": "direct"}
    ]
  }
}
```

### Clash Meta

```yaml
rules:
  - GEOIP,WHITELIST-RU,DIRECT
  - GEOSITE,WHITELIST-RU,DIRECT
```

## Кастомизация (include / exclude)

Можно **добавлять** или **удалять** отдельные IP/домены в любой категории через
списки в каталоге [`custom/`](custom/), не трогая исходники. Имя файла = имя
категории:

```
custom/geoip/include/<категория>.txt    # добавить IP/CIDR
custom/geoip/exclude/<категория>.txt    # удалить IP/CIDR (точное вычитание диапазона)
custom/geosite/include/<категория>.txt  # добавить доменное правило
custom/geosite/exclude/<категория>.txt  # удалить доменное правило
```

Подробности синтаксиса и правил валидации — в [custom/README.md](custom/README.md).

## Локальная сборка

`geoip.dat` собирается на Python. `geosite.dat` собирается из исходников
сборщиком [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
(нужен Go).

```bash
pip install -r requirements.txt
python scripts/fetch_sources.py            # скачать geoip.dat
python scripts/parse_whitelist.py          # получить whitelist IP/домены
python scripts/patch_geoip.py              # -> output/geoip.dat (WHITELIST-RU + overlays)
python scripts/build_geosite_data.py       # -> downloads/geosite-data/ (исходники + overlays)

# geosite.dat: скомпилировать подготовленное дерево сборщиком v2fly
git clone --depth 1 https://github.com/v2fly/domain-list-community community
cp -a downloads/geosite-data/. community/data/
(cd community && go run ./ -outputdir=/tmp/out)
cp /tmp/out/dlc.dat output/geosite.dat

python scripts/validate_build.py           # проверка инвариантов
```

Результаты в `output/geoip.dat` и `output/geosite.dat`.

## Источники

- [hydraponique/roscomvpn-geoip](https://github.com/hydraponique/roscomvpn-geoip) - базовый GeoIP файл
- [hydraponique/roscomvpn-geosite](https://github.com/hydraponique/roscomvpn-geosite) - исходники GeoSite категорий (`data/`)
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) - сборщик geosite.dat
- [kirilllavrov/whitelists](https://github.com/kirilllavrov/whitelists) - whitelist данные (IP и RU-домены)

## Лицензия

[MIT License](LICENSE)
