# Custom overlays (include / exclude)

This directory lets you **add** or **remove** specific IPs and domains from the
generated `geoip.dat` / `geosite.dat`, per category, without touching the
upstream sources. The build applies these overlays on every run.

## Layout

```
custom/
  geoip/
    include/<category>.txt   # CIDRs/IPs to ADD to that geoip category
    exclude/<category>.txt   # CIDRs/IPs to REMOVE from that geoip category
  geosite/
    include/<category>.txt   # domain rules to ADD to that geosite category
    exclude/<category>.txt   # domain rules to REMOVE from that geosite category
```

The **file name is the category name** (lowercase). Categories:

- **geoip:** `direct`, `private`, `whitelist`, `whitelist-ru`
- **geosite:** `apple`, `category-ads`, `category-geoblock-ru`, `category-ru`,
  `epicgames`, `escapefromtarkov`, `faceit`, `github`, `google-deepmind`,
  `google-play`, `microsoft`, `origin`, `pinterest`, `private`, `riot`,
  `steam`, `telegram`, `torrent`, `twitch`, `twitch-ads`, `whitelist`,
  `win-spy`, `youtube`, `whitelist-ru`

All files start empty. Fill them as needed. Blank lines and lines starting with
`#` are ignored. A missing file is treated the same as an empty one.

## geoip entries

One IPv4/IPv6 address or CIDR per line:

```
1.2.3.4
5.6.7.0/24
2001:db8::/32
```

- **include:** the CIDR is added to the category. If it is already covered by an
  existing entry it is skipped (logged as a warning).
- **exclude:** the range is removed by exact set subtraction. Excluding
  `5.6.7.0/25` from a category that contains `5.6.7.0/24` splits the covering
  network into the remaining halves. An exclude that matches nothing is a
  warning (stale entry), not an error.

## geosite entries

One domain rule per line, using the same syntax as the upstream `data/` files:

```
domain:example.com     # example.com and all subdomains (default if no prefix)
example.com            # same as domain:example.com
full:example.com       # exact match only, no subdomains
keyword:example        # substring match
regexp:.*\.example\.com$
```

Internationalized domains (e.g. `мвд.рф`) are converted to punycode
automatically.

- **include:** the rule is appended to the category. An identical rule that
  already exists is skipped (warning).
- **exclude:** rules matching **exactly** (same type + value) are removed. A
  warning is logged if nothing matched.

### exclude is an exact-rule match

Exclude removes only the exact rule you list. It does **not** remove entries
that a broader rule would still cover — e.g. excluding `domain:ads.example.com`
does nothing if the category only contains `domain:example.com` (which already
matches `ads.example.com`). To carve out a subdomain, exclude the broad rule and
re-add the parts you want with `include`.

## Validation & logs

Every build prints per-category counters (added / skipped-duplicate / removed /
unmatched). Problems in **your** overlay files (bad IP, bad domain, or the same
entry in both include and exclude of one category) fail the build. Divergence
from upstream (a stale exclude that no longer matches) is only a warning, and
unmatched excludes are also surfaced in the GitHub Actions step summary.

After the build, invariants are checked: every category must be present and
non-empty, no category may lose more than the allowed share of its entries
versus the previous release, and every category referenced by `JSON.DEFAULT`
must exist. If any invariant fails, no release is published and users stay on
the previous one.
