#!/usr/bin/env python3
"""
Test the fixed XTC parsing approach
"""

from xtc1reader import XTCReader
from xtc1reader.xtc_reader import walk_xtc_tree
from xtc1reader.data_types import parse_detector_data, get_type_description, is_image_type


def test_corrected_parsing(filename: str, max_events: int = 10):
    """Test XTC parsing with corrected payload handling"""
    
    print(f"Testing corrected XTC parsing: {filename}")
    print("=" * 60)
    
    target_types = {117, 118}  # Corrected experimental TypeIds for Epix10ka2M
    found_types = set()
    
    with XTCReader(filename) as reader:
        for i, (dgram, full_payload) in enumerate(reader):
            if i >= max_events:
                break
                
            print(f"\nEvent {i}:")
            print(f"  Time: {dgram.seq.clock.as_double():.6f}s")
            print(f"  Full payload size: {len(full_payload)} bytes")
            print(f"  XTC extent: {dgram.xtc.extent}")
            print(f"  XTC contains: type={dgram.xtc.contains.type_id}, version={dgram.xtc.contains.version}")
            
            # The issue: full_payload includes 16 bytes of XTC header remainder
            # We need to skip these to get to actual nested XTC containers
            if len(full_payload) > 16:
                actual_payload = full_payload[16:]  # Skip the XTC header remainder
                print(f"  Actual XTC payload size: {len(actual_payload)} bytes")
                
                if len(actual_payload) > 0:
                    print(f"  Walking XTC tree with corrected payload...")
                    
                    try:
                        tree = walk_xtc_tree(actual_payload, max_level=3)
                        
                        all_types = set()
                        important_containers = []
                        
                        for level, xtc, data in tree:
                            type_id = xtc.contains.type_id
                            all_types.add(type_id)
                            
                            # Check for experimental TypeIds we're looking for
                            if type_id in target_types:
                                found_types.add(type_id)
                                important_containers.append((level, xtc, data))
                                
                            # Also check for any image types
                            if is_image_type(type_id):
                                important_containers.append((level, xtc, data))
                        
                        print(f"  Found types: {sorted(all_types)}")
                        
                        # Print details for experimental types and image types
                        if important_containers:
                            print(f"  🎯 Important containers found:")
                            for level, xtc, data in important_containers:
                                indent = "    " * (level + 1)
                                type_desc = get_type_description(xtc.contains.type_id)
                                is_img = is_image_type(xtc.contains.type_id)
                                
                                print(f"{indent}Type {xtc.contains.type_id}: {type_desc}")
                                print(f"{indent}  Extent: {xtc.extent}, Data size: {len(data) if data else 0}")
                                print(f"{indent}  Is image type: {is_img}")
                                
                                if data and len(data) > 0:
                                    print(f"{indent}  🎯 Found detector data! Attempting to parse...")
                                    try:
                                        parsed_data = parse_detector_data(data, xtc.contains.type_id, xtc.contains.version)
                                        if hasattr(parsed_data, 'frames'):
                                            print(f"{indent}  ✅ Successfully parsed! Shape: {parsed_data.frames.shape}")
                                        else:
                                            print(f"{indent}  ⚠️  Parsed but no frames attribute: {type(parsed_data)}")
                                    except Exception as e:
                                        print(f"{indent}  ❌ Parse failed: {e}")
                        
                        if not tree:
                            print("    No XTC containers found in corrected payload")
                            
                    except Exception as e:
                        print(f"    Error walking XTC tree: {e}")
                else:
                    print("    No actual payload data after XTC header")
            else:
                print("    Payload too small to contain XTC header remainder")
                
            # Early exit if we found all target types
            if found_types == target_types:
                print(f"\n🎉 Found all target experimental TypeIds: {sorted(found_types)}")
                break
    
    print(f"\nSummary:")
    print(f"  Target TypeIds: {sorted(target_types)}")
    print(f"  Found TypeIds: {sorted(found_types)}")
    missing = target_types - found_types
    if missing:
        print(f"  Missing TypeIds: {sorted(missing)}")
    else:
        print(f"  ✅ All experimental TypeIds found!")


def main():
    test_corrected_parsing("/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s00-c00.xtc")


if __name__ == "__main__":
    main()