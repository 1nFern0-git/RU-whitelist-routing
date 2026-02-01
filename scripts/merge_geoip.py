#!/usr/bin/env python3
"""
merge_geoip.py - Merge whitelist IPs into geoip.dat (V2Ray protobuf format)
"""
import sys
import os
from pathlib import Path
import struct


def read_varint(data, offset):
    """
    Read a varint from bytes
    
    Args:
        data: Bytes to read from
        offset: Starting offset
        
    Returns:
        Tuple of (value, new_offset)
    """
    result = 0
    shift = 0
    pos = offset
    
    while True:
        if pos >= len(data):
            raise ValueError("Incomplete varint")
        
        byte = data[pos]
        pos += 1
        
        result |= (byte & 0x7F) << shift
        
        if (byte & 0x80) == 0:
            break
        
        shift += 7
    
    return result, pos


def write_varint(value):
    """
    Encode an integer as a varint
    
    Args:
        value: Integer to encode
        
    Returns:
        Bytes representing the varint
    """
    result = bytearray()
    
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    
    result.append(value & 0x7F)
    
    return bytes(result)


def ip_to_bytes(ip_str):
    """
    Convert IP address string to bytes
    
    Args:
        ip_str: IP address as string (e.g., "192.168.1.1" or "192.168.1.0/24")
        
    Returns:
        Tuple of (ip_bytes, prefix)
    """
    # Split IP and prefix
    if '/' in ip_str:
        ip_part, prefix_str = ip_str.split('/')
        prefix = int(prefix_str)
    else:
        ip_part = ip_str
        prefix = 32  # Default /32 for single IP
    
    # Convert IP to bytes
    parts = ip_part.split('.')
    ip_bytes = bytes([int(p) for p in parts])
    
    return ip_bytes, prefix


def create_cidr_entry(ip, prefix):
    """
    Create a CIDR entry in protobuf format
    
    Args:
        ip: IP address as bytes
        prefix: Prefix length (0-32)
        
    Returns:
        Encoded CIDR entry
    """
    result = bytearray()
    
    # Field 1: IP (bytes)
    result.append(0x0A)  # Field number 1, wire type 2 (length-delimited)
    result.extend(write_varint(len(ip)))
    result.extend(ip)
    
    # Field 2: Prefix (uint32)
    result.append(0x10)  # Field number 2, wire type 0 (varint)
    result.extend(write_varint(prefix))
    
    return bytes(result)


def encode_geoip_entry(country_code, cidrs):
    """
    Encode a GeoIP entry in protobuf format
    
    Args:
        country_code: Country code string
        cidrs: List of CIDR entries (bytes)
        
    Returns:
        Encoded GeoIP entry
    """
    result = bytearray()
    
    # Field 1: country_code (string)
    result.append(0x0A)  # Field number 1, wire type 2
    country_bytes = country_code.encode('utf-8')
    result.extend(write_varint(len(country_bytes)))
    result.extend(country_bytes)
    
    # Field 2: repeated cidr
    for cidr in cidrs:
        result.append(0x12)  # Field number 2, wire type 2
        result.extend(write_varint(len(cidr)))
        result.extend(cidr)
    
    return bytes(result)


def main():
    """Main function"""
    base_dir = Path(__file__).parent.parent
    
    # Input files
    geoip_input = base_dir / 'downloads' / 'geoip.dat'
    ips_file = base_dir / 'data' / 'whitelist_ips.txt'
    
    # Output file
    output_dir = base_dir / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    geoip_output = output_dir / 'geoip.dat'
    
    # Check input files exist
    if not geoip_input.exists():
        print(f"ERROR: {geoip_input} not found", file=sys.stderr)
        return 1
    
    if not ips_file.exists():
        print(f"ERROR: {ips_file} not found", file=sys.stderr)
        return 1
    
    # Read original geoip.dat
    print("Reading original geoip.dat...", file=sys.stderr)
    with open(geoip_input, 'rb') as f:
        original_data = f.read()
    
    print(f"Original size: {len(original_data)} bytes", file=sys.stderr)
    
    # Read whitelist IPs
    print("Reading whitelist IPs...", file=sys.stderr)
    with open(ips_file, 'r') as f:
        ip_list = [line.strip() for line in f if line.strip()]
    
    print(f"Total IPs: {len(ip_list)}", file=sys.stderr)
    
    # Create CIDR entries for whitelist
    print("Creating WHITELIST category...", file=sys.stderr)
    cidrs = []
    for ip_str in ip_list:
        try:
            ip_bytes, prefix = ip_to_bytes(ip_str)
            cidr_entry = create_cidr_entry(ip_bytes, prefix)
            cidrs.append(cidr_entry)
        except Exception as e:
            print(f"WARNING: Failed to parse IP {ip_str}: {e}", file=sys.stderr)
    
    print(f"Created {len(cidrs)} CIDR entries", file=sys.stderr)
    
    # Encode WHITELIST entry
    whitelist_entry = encode_geoip_entry('WHITELIST', cidrs)
    print(f"WHITELIST entry size: {len(whitelist_entry)} bytes", file=sys.stderr)
    
    # Wrap entry with field tag for GeoIPList.entry (field 1, wire type 2)
    wrapped_entry = bytearray()
    wrapped_entry.append(0x0A)  # Field 1, wire type 2
    wrapped_entry.extend(write_varint(len(whitelist_entry)))
    wrapped_entry.extend(whitelist_entry)
    
    # Combine original data with new entry
    output_data = original_data + bytes(wrapped_entry)
    
    # Write output file
    print(f"Writing to {geoip_output}...", file=sys.stderr)
    with open(geoip_output, 'wb') as f:
        f.write(output_data)
    
    print(f"\nOutput size: {len(output_data)} bytes", file=sys.stderr)
    print(f"Added: {len(whitelist_entry)} bytes", file=sys.stderr)
    print(f"Successfully created geoip.dat with WHITELIST category!", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
