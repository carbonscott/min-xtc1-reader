#!/usr/bin/env python3
"""
Debug XTC parsing to identify the root cause of "extent exceeds payload" errors
"""

import struct
import sys
from xtc1reader import XTCReader
from xtc1reader.binary_format import parse_xtc_header, parse_datagram_header


def debug_binary_data(filename: str, max_bytes: int = 1000):
    """Debug raw binary data from XTC file"""
    print(f"Debugging XTC file: {filename}")
    print("=" * 60)
    
    with open(filename, 'rb') as f:
        data = f.read(max_bytes)
    
    print("Raw hex dump of first 200 bytes:")
    for i in range(0, min(200, len(data)), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{i:04x}: {hex_str:<48} |{ascii_str}|")
    
    print("\n" + "=" * 60)
    
    # Parse datagram header (first 36 bytes)
    if len(data) >= 36:
        print("Parsing datagram header:")
        try:
            dgram = parse_datagram_header(data[:36])
            print(f"  Sequence: clock={dgram.seq.clock.as_double():.6f}s")
            print(f"  Environment: {dgram.env}")
            print(f"  Main XTC:")
            print(f"    Damage: 0x{dgram.xtc.damage.value:08x}")
            print(f"    Src: log=0x{dgram.xtc.src.log:08x}, phy=0x{dgram.xtc.src.phy:08x}")
            print(f"    Contains: type={dgram.xtc.contains.type_id}, version={dgram.xtc.contains.version}")
            print(f"    Extent: {dgram.xtc.extent} bytes")
            
            # Check if extent is reasonable
            if dgram.xtc.extent > len(data):
                print(f"    ⚠️  WARNING: Extent {dgram.xtc.extent} > available data {len(data)}")
            else:
                print(f"    ✅ Extent appears reasonable")
                
        except Exception as e:
            print(f"  Error parsing datagram: {e}")
    
    print("\n" + "=" * 60)
    
    # Try to parse payload XTC containers manually
    if len(data) >= 56:  # 36 (datagram) + 20 (first XTC)
        print("Parsing first payload XTC container:")
        payload_start = 36
        
        try:
            # Parse first XTC in payload
            xtc = parse_xtc_header(data, payload_start)
            print(f"  Damage: 0x{xtc.damage.value:08x}")
            print(f"  Src: log=0x{xtc.src.log:08x}, phy=0x{xtc.src.phy:08x}")
            print(f"  Contains: type={xtc.contains.type_id}, version={xtc.contains.version}")
            print(f"  Extent: {xtc.extent} bytes")
            
            # Check extent reasonableness
            remaining_data = len(data) - payload_start
            if xtc.extent > remaining_data:
                print(f"  ⚠️  WARNING: Extent {xtc.extent} > remaining data {remaining_data}")
                print(f"  This explains the 'extent exceeds payload' error!")
                
                # Show the raw bytes that were interpreted as extent
                extent_bytes = data[payload_start + 16:payload_start + 20]
                print(f"  Raw extent bytes: {extent_bytes.hex()}")
                print(f"  As little-endian uint32: {struct.unpack('<I', extent_bytes)[0]}")
                print(f"  As big-endian uint32: {struct.unpack('>I', extent_bytes)[0]}")
                
            else:
                print(f"  ✅ Extent appears reasonable for payload")
                
        except Exception as e:
            print(f"  Error parsing payload XTC: {e}")


def debug_xtc_reader(filename: str, max_events: int = 3):
    """Debug XTC reader event by event"""
    print(f"\nDebugging XTC reader for: {filename}")
    print("=" * 60)
    
    try:
        with XTCReader(filename) as reader:
            for i, (dgram, payload) in enumerate(reader):
                if i >= max_events:
                    break
                    
                print(f"\nEvent {i}:")
                print(f"  Time: {dgram.seq.clock.as_double():.6f}s")
                print(f"  Payload size: {len(payload)} bytes")
                print(f"  Main XTC extent: {dgram.xtc.extent}")
                
                # Check if main XTC extent makes sense
                expected_payload = dgram.xtc.extent - 20  # Subtract XTC header size
                if len(payload) != expected_payload:
                    print(f"  ⚠️  Payload size mismatch: expected {expected_payload}, got {len(payload)}")
                
                # Try to parse first XTC in payload
                if len(payload) >= 20:
                    try:
                        first_xtc = parse_xtc_header(payload, 0)
                        print(f"  First payload XTC:")
                        print(f"    Type: {first_xtc.contains.type_id}")
                        print(f"    Extent: {first_xtc.extent}")
                        
                        if first_xtc.extent > len(payload):
                            print(f"    ⚠️  First XTC extent {first_xtc.extent} > payload {len(payload)}")
                        else:
                            print(f"    ✅ First XTC extent looks good")
                            
                    except Exception as e:
                        print(f"    Error parsing first payload XTC: {e}")
                        
    except Exception as e:
        print(f"Error with XTC reader: {e}")


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = "/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s00-c00.xtc"
    
    # Debug binary data first
    debug_binary_data(filename)
    
    # Then debug XTC reader
    debug_xtc_reader(filename)


if __name__ == "__main__":
    main()