#!/usr/bin/env python3
"""
Search for experimental TypeIds 6185, 6190, 6193 across multiple XTC files
"""

import os
import glob
from xtc1reader import XTCReader
from xtc1reader.xtc_reader import walk_xtc_tree

def search_typeids_in_file(filename: str, target_types: set, max_events: int = 50):
    """Search for target TypeIds in a single XTC file"""
    found_types = set()
    
    try:
        with XTCReader(filename) as reader:
            for i, (dgram, full_payload) in enumerate(reader):
                if i >= max_events:
                    break
                    
                # Skip first 16 bytes of payload (XTC header remainder) for tree walking  
                if len(full_payload) > 16:
                    actual_payload = full_payload[16:]
                    
                    if len(actual_payload) > 0:
                        try:
                            tree = walk_xtc_tree(actual_payload, max_level=3)
                            
                            for level, xtc, data in tree:
                                type_id = xtc.contains.type_id
                                if type_id in target_types:
                                    found_types.add(type_id)
                                    print(f"  🎯 Found TypeId {type_id} in event {i}")
                                    
                        except Exception as e:
                            pass  # Skip errors for now
                            
                # Early exit if we found all target types
                if found_types == target_types:
                    break
                    
    except Exception as e:
        print(f"  Error reading file: {e}")
        
    return found_types

def search_experimental_typeids(base_path: str, target_types: set):
    """Search for experimental TypeIds across multiple XTC files"""
    
    print(f"Searching for experimental TypeIds: {sorted(target_types)}")
    print("=" * 60)
    
    # Look for XTC files - try different run ranges
    patterns = [
        "mfx100903824-r00*-s00-c00.xtc",  # Early runs
        "mfx100903824-r01*-s00-c00.xtc",  # r010x runs
        "mfx100903824-r02*-s00-c00.xtc",  # r020x runs  
        "mfx100903824-r03*-s00-c00.xtc",  # r030x runs
    ]
    
    files = []
    for pattern in patterns:
        pattern_files = sorted(glob.glob(os.path.join(base_path, pattern)))[:5]  # 5 from each range
        files.extend(pattern_files)
    
    if not files:
        print(f"No XTC files found with pattern: {pattern}")
        return set()
    
    print(f"Found {len(files)} XTC files to search")
    
    all_found_types = set()
    
    for i, filename in enumerate(files):
        print(f"\nSearching file {i+1}/{len(files)}: {os.path.basename(filename)}")
        found_types = search_typeids_in_file(filename, target_types, max_events=20)
        
        if found_types:
            print(f"  ✅ Found TypeIds: {sorted(found_types)}")
            all_found_types.update(found_types)
        else:
            print(f"  ❌ No target TypeIds found")
            
        # Early exit if we found all target types
        if all_found_types == target_types:
            print(f"\n🎉 Found all target experimental TypeIds!")
            break
    
    print(f"\nFinal Summary:")
    print(f"  Target TypeIds: {sorted(target_types)}")
    print(f"  Found TypeIds: {sorted(all_found_types)}")
    missing = target_types - all_found_types
    if missing:
        print(f"  Missing TypeIds: {sorted(missing)}")
        
        # If we didn't find them, try a few more runs
        if len(files) < 20:
            print(f"\nTrying additional runs...")
            pattern = os.path.join(base_path, "mfx100903824-r02*-s00-c00.xtc")  
            additional_files = sorted(glob.glob(pattern))[:5]
            
            for filename in additional_files:
                print(f"\nSearching additional file: {os.path.basename(filename)}")
                found_types = search_typeids_in_file(filename, missing, max_events=20)
                
                if found_types:
                    print(f"  ✅ Found TypeIds: {sorted(found_types)}")
                    all_found_types.update(found_types)
                    
                if all_found_types == target_types:
                    print(f"\n🎉 Found all target experimental TypeIds!")
                    break
    else:
        print(f"  ✅ All experimental TypeIds found!")
        
    return all_found_types

def main():
    base_path = "/sdf/data/lcls/ds/mfx/mfx100903824/xtc"
    target_types = {6185, 6190, 6193}
    
    found_types = search_experimental_typeids(base_path, target_types)
    
    if found_types == target_types:
        print(f"\n✅ SUCCESS: All experimental TypeIds found!")
        print(f"   This confirms the XTC parsing fix is working correctly.")
    else:
        missing = target_types - found_types
        print(f"\n⚠️  Still missing TypeIds: {sorted(missing)}")
        print(f"   These may be in different runs or require deeper search.")

if __name__ == "__main__":
    main()