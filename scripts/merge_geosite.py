#!/usr/bin/env python3
"""
merge_geosite.py - Merge whitelist domains into geosite.dat (V2Ray protobuf format)
"""
import sys
from pathlib import Path


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


def create_domain_entry(domain, domain_type=2):
    """
    Create a Domain entry in protobuf format
    
    Args:
        domain: Domain name string
        domain_type: Type of domain (2 = Domain with subdomains)
        
    Returns:
        Encoded Domain entry
    """
    result = bytearray()
    
    # Field 1: type (enum, as varint)
    result.append(0x08)  # Field number 1, wire type 0
    result.extend(write_varint(domain_type))
    
    # Field 2: value (string)
    result.append(0x12)  # Field number 2, wire type 2
    domain_bytes = domain.encode('utf-8')
    result.extend(write_varint(len(domain_bytes)))
    result.extend(domain_bytes)
    
    return bytes(result)


def encode_geosite_entry(country_code, domains):
    """
    Encode a GeoSite entry in protobuf format
    
    Args:
        country_code: Country code string
        domains: List of domain entries (bytes)
        
    Returns:
        Encoded GeoSite entry
    """
    result = bytearray()
    
    # Field 1: country_code (string)
    result.append(0x0A)  # Field number 1, wire type 2
    country_bytes = country_code.encode('utf-8')
    result.extend(write_varint(len(country_bytes)))
    result.extend(country_bytes)
    
    # Field 2: repeated domain
    for domain in domains:
        result.append(0x12)  # Field number 2, wire type 2
        result.extend(write_varint(len(domain)))
        result.extend(domain)
    
    return bytes(result)


def main():
    """Main function"""
    base_dir = Path(__file__).parent.parent
    
    # Input files
    geosite_input = base_dir / 'downloads' / 'geosite.dat'
    ru_domains_file = base_dir / 'data' / 'whitelist_ru_domains.txt'

    # Output file
    output_dir = base_dir / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    geosite_output = output_dir / 'geosite.dat'

    # Check input files exist
    if not geosite_input.exists():
        print(f"ERROR: {geosite_input} not found", file=sys.stderr)
        return 1

    if not ru_domains_file.exists():
        print(f"ERROR: {ru_domains_file} not found", file=sys.stderr)
        return 1

    # Read original geosite.dat
    print("Reading original geosite.dat...", file=sys.stderr)
    with open(geosite_input, 'rb') as f:
        original_data = f.read()

    print(f"Original size: {len(original_data)} bytes", file=sys.stderr)

    # Read RU domains
    print("\nReading WHITELIST-RU domains...", file=sys.stderr)
    with open(ru_domains_file, 'r', encoding='utf-8') as f:
        ru_domains = [line.strip() for line in f if line.strip()]

    print(f"Total RU domains: {len(ru_domains)}", file=sys.stderr)

    # Create domain entries for WHITELIST-RU
    print("Creating WHITELIST-RU category...", file=sys.stderr)
    ru_domain_entries = []
    for domain in ru_domains:
        # 'full:' prefix means exact match (type 3) instead of the
        # default root-domain/subdomain match (type 2)
        domain_type = 2
        if domain.startswith('full:'):
            domain_type = 3
            domain = domain[5:]
        try:
            entry = create_domain_entry(domain, domain_type=domain_type)
            ru_domain_entries.append(entry)
        except UnicodeEncodeError as e:
            print(f"WARNING: Failed to encode domain {domain}: {e}", file=sys.stderr)

    print(f"Created {len(ru_domain_entries)} domain entries", file=sys.stderr)

    # Encode WHITELIST-RU entry
    whitelist_ru_entry = encode_geosite_entry('WHITELIST-RU', ru_domain_entries)
    print(f"WHITELIST-RU entry size: {len(whitelist_ru_entry)} bytes", file=sys.stderr)

    # Wrap entry with field tag for GeoSiteList.entry
    wrapped_data = bytearray()
    wrapped_data.append(0x0A)  # Field 1, wire type 2
    wrapped_data.extend(write_varint(len(whitelist_ru_entry)))
    wrapped_data.extend(whitelist_ru_entry)

    # Combine original data with new entry
    output_data = original_data + bytes(wrapped_data)

    # Write output file
    print(f"\nWriting to {geosite_output}...", file=sys.stderr)
    with open(geosite_output, 'wb') as f:
        f.write(output_data)

    print(f"\nOutput size: {len(output_data)} bytes", file=sys.stderr)
    print(f"Added WHITELIST-RU: {len(whitelist_ru_entry)} bytes ({len(ru_domain_entries)} domains)", file=sys.stderr)
    print(f"Successfully created geosite.dat with WHITELIST-RU category!", file=sys.stderr)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
