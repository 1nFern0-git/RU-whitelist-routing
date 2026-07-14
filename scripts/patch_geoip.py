#!/usr/bin/env python3
"""
patch_geoip.py - Rebuild geoip.dat from the upstream download plus our overlays.

Pipeline (replaces the old binary-append merge_geoip.py):
  1. Decode downloads/geoip.dat (V2Ray GeoIPList protobuf) into categories.
  2. Add the WHITELIST-RU category from data/whitelist_ips.txt.
  3. Apply custom/geoip/include and custom/geoip/exclude overlays per category.
  4. Re-encode to output/geoip.dat.

Excludes use exact range subtraction (ipaddress.address_exclude), so removing a
subnet splits any covering network instead of dropping it wholesale.
"""
import sys
import json
import ipaddress
from pathlib import Path

from overlay_common import (
    warn, fail, append_step_summary, load_overlay_entries, Counters,
)


# ---------------------------------------------------------------------------
# protobuf primitives
# ---------------------------------------------------------------------------

def read_varint(data, pos):
    """Read a base-128 varint. Returns (value, new_pos)."""
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7


def write_varint(value):
    """Encode a non-negative integer as a varint."""
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value & 0x7F)
    return bytes(out)


def iter_fields(data):
    """
    Walk a protobuf message. Yields (field_num, wire_type, value, raw) where
    value is an int (varint/fixed) or bytes (length-delimited) and raw is the
    original tag+payload slice (for verbatim pass-through of unknown fields).
    """
    pos = 0
    n = len(data)
    while pos < n:
        start = pos
        tag, pos = read_varint(data, pos)
        field = tag >> 3
        wire = tag & 0x07
        if wire == 0:
            val, pos = read_varint(data, pos)
        elif wire == 2:
            length, pos = read_varint(data, pos)
            val = data[pos:pos + length]
            pos += length
        elif wire == 5:
            val = data[pos:pos + 4]
            pos += 4
        elif wire == 1:
            val = data[pos:pos + 8]
            pos += 8
        else:
            raise ValueError(f"unsupported wire type {wire}")
        yield field, wire, val, data[start:pos]


def tag(field, wire):
    return write_varint((field << 3) | wire)


def ldelim(field, payload):
    """Encode a length-delimited field (wire type 2)."""
    return tag(field, 2) + write_varint(len(payload)) + payload


# ---------------------------------------------------------------------------
# GeoIP decode / encode
# ---------------------------------------------------------------------------

def decode_cidr(data):
    """Return (ip_bytes, prefix, extras) for a CIDR message."""
    ip = None
    prefix = None
    extras = []
    for field, wire, val, raw in iter_fields(data):
        if field == 1 and wire == 2:
            ip = val
        elif field == 2 and wire == 0:
            prefix = val
        else:
            extras.append(raw)
    if ip is None or prefix is None:
        raise ValueError("CIDR missing ip/prefix")
    return ip, prefix, extras


def decode_entry(data):
    """Return dict{cc, nets:[ip_network], extras:[raw]} for a GeoIP entry."""
    cc = None
    nets = []
    extras = []
    for field, wire, val, raw in iter_fields(data):
        if field == 1 and wire == 2:
            cc = val.decode('utf-8')
        elif field == 2 and wire == 2:
            ip, prefix, cidr_extras = decode_cidr(val)
            if cidr_extras:
                warn(f"CIDR in {cc} carries unknown fields; dropping them")
            nets.append(net_from_bytes(ip, prefix))
        else:
            extras.append(raw)
    if cc is None:
        raise ValueError("GeoIP entry missing country_code")
    return {'cc': cc, 'nets': nets, 'extras': extras}


def decode_geoip(data):
    """Decode a GeoIPList into an ordered list of entry dicts."""
    entries = []
    for field, wire, val, raw in iter_fields(data):
        if field == 1 and wire == 2:
            entries.append(decode_entry(val))
        else:
            warn(f"ignoring unexpected top-level field {field} in geoip.dat")
    return entries


def net_from_bytes(ip_bytes, prefix):
    """Build an ip_network from packed address bytes + prefix length."""
    if len(ip_bytes) == 4:
        return ipaddress.IPv4Network((ipaddress.IPv4Address(ip_bytes), prefix))
    if len(ip_bytes) == 16:
        return ipaddress.IPv6Network((ipaddress.IPv6Address(ip_bytes), prefix))
    raise ValueError(f"unexpected IP byte length {len(ip_bytes)}")


def encode_cidr(net):
    payload = ldelim(1, net.network_address.packed) + tag(2, 0) + write_varint(net.prefixlen)
    return payload


def encode_entry(entry):
    payload = bytearray()
    payload += ldelim(1, entry['cc'].encode('utf-8'))
    for net in entry['nets']:
        payload += ldelim(2, encode_cidr(net))
    for raw in entry['extras']:
        payload += raw
    return bytes(payload)


def encode_geoip(entries):
    out = bytearray()
    for entry in entries:
        out += ldelim(1, encode_entry(entry))
    return bytes(out)


# ---------------------------------------------------------------------------
# overlay parsing / application
# ---------------------------------------------------------------------------

def parse_cidr(text):
    """Parse an IP/CIDR string into a normalized ip_network, or None if invalid."""
    try:
        if '/' in text:
            return ipaddress.ip_network(text, strict=False)
        addr = ipaddress.ip_address(text)
        prefix = 32 if addr.version == 4 else 128
        return ipaddress.ip_network((addr, prefix))
    except ValueError:
        return None


def covered_by(net, existing):
    """True if net is equal to or a subnet of any network in existing."""
    for other in existing:
        if other.version != net.version:
            continue
        if net == other or net.subnet_of(other):
            return True
    return False


def apply_geoip_overlays(entry, overlay_dir, counters, unmatched_report):
    """Apply include/exclude overlays to one GeoIP entry (in place)."""
    category = entry['cc'].lower()

    includes = load_overlay_entries(overlay_dir, 'include', category)
    excludes = load_overlay_entries(overlay_dir, 'exclude', category)

    inc_nets = {}
    for lineno, text in includes:
        net = parse_cidr(text)
        if net is None:
            fail(f"custom/geoip/include/{category}.txt:{lineno}: invalid IP/CIDR '{text}'")
        inc_nets[net] = lineno

    exc_nets = {}
    for lineno, text in excludes:
        net = parse_cidr(text)
        if net is None:
            fail(f"custom/geoip/exclude/{category}.txt:{lineno}: invalid IP/CIDR '{text}'")
        exc_nets[net] = lineno

    conflict = set(inc_nets) & set(exc_nets)
    if conflict:
        listed = ', '.join(str(n) for n in sorted(conflict, key=str))
        fail(f"geoip category '{category}': {listed} appear in both include and exclude")

    # Includes: append unless already covered.
    for net in inc_nets:
        if covered_by(net, entry['nets']):
            warn(f"geoip include {net} already covered in '{category}'; skipping")
            counters.skipped_dup += 1
        else:
            entry['nets'].append(net)
            counters.added += 1

    # Excludes: exact range subtraction (split covering networks).
    for exc in exc_nets:
        new_nets = []
        matched = False
        for net in entry['nets']:
            if net.version != exc.version:
                new_nets.append(net)
                continue
            if net == exc or net.subnet_of(exc):
                matched = True  # drop entirely
            elif net.supernet_of(exc):
                matched = True
                new_nets.extend(net.address_exclude(exc))
            else:
                new_nets.append(net)
        entry['nets'] = new_nets
        if matched:
            counters.removed += 1
        else:
            counters.unmatched += 1
            warn(f"geoip exclude {exc} matched nothing in '{category}' (stale?)")
            unmatched_report.append(f"- `geoip:{category}` exclude `{exc}` — no match")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_whitelist_ru_entry(ips_file):
    """Build the WHITELIST-RU entry from the parsed whitelist IP list."""
    nets = []
    if not ips_file.exists():
        fail(f"{ips_file} not found (run parse_whitelist.py first)")
    for line in ips_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        net = parse_cidr(line)
        if net is None:
            warn(f"skipping invalid whitelist IP '{line}'")
            continue
        nets.append(net)
    return {'cc': 'WHITELIST-RU', 'nets': nets, 'extras': []}


def main():
    base_dir = Path(__file__).parent.parent
    geoip_input = base_dir / 'downloads' / 'geoip.dat'
    ips_file = base_dir / 'data' / 'whitelist_ips.txt'
    overlay_dir = base_dir / 'custom' / 'geoip'
    output_dir = base_dir / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    geoip_output = output_dir / 'geoip.dat'

    if not geoip_input.exists():
        fail(f"{geoip_input} not found (run fetch_sources.py first)")

    print("Decoding geoip.dat...", file=sys.stderr)
    entries = decode_geoip(geoip_input.read_bytes())
    summary = ', '.join("{0}({1})".format(e['cc'], len(e['nets'])) for e in entries)
    print(f"  {len(entries)} categories: {summary}", file=sys.stderr)

    # Add WHITELIST-RU (replace if upstream ever ships one).
    entries = [e for e in entries if e['cc'].upper() != 'WHITELIST-RU']
    wl_ru = build_whitelist_ru_entry(ips_file)
    entries.append(wl_ru)
    print(f"Added WHITELIST-RU: {len(wl_ru['nets'])} CIDRs", file=sys.stderr)

    print("Applying geoip overlays...", file=sys.stderr)
    unmatched_report = []
    for entry in entries:
        counters = Counters()
        apply_geoip_overlays(entry, overlay_dir, counters, unmatched_report)
        if counters.nonzero():
            print(counters.report_line(entry['cc']), file=sys.stderr)

    data = encode_geoip(entries)
    geoip_output.write_bytes(data)
    print(f"Wrote {geoip_output} ({len(data)} bytes, "
          f"{sum(len(e['nets']) for e in entries)} CIDRs total)", file=sys.stderr)

    if unmatched_report:
        append_step_summary(["### geoip: unmatched excludes", *unmatched_report])

    return 0


if __name__ == '__main__':
    sys.exit(main())
