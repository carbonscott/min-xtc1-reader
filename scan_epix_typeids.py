#!/usr/bin/env python3
"""
TypeId Discovery Script for Epix Detectors

Scans XTC files to identify TypeId values associated with Epix detectors.
This helps us understand what numeric values to look for when parsing Epix data.
"""

import sys
import os
from collections import defaultdict
from pathlib import Path

# Add the package to path
sys.path.insert(0, os.path.abspath('.'))

from xtc1reader import XTCReader, walk_xtc_tree

def scan_file_for_typeids(filename):
    """Scan a single XTC file and collect all TypeId values with metadata"""
    typeids = defaultdict(lambda: {
        'count': 0, 
        'sources': set(), 
        'extents': [], 
        'damage_flags': set()
    })
    
    print(f"Scanning: {filename}")
    
    try:
        with XTCReader(filename) as reader:
            event_count = 0
            for dgram, payload in reader:
                event_count += 1
                
                # Walk the XTC tree in this event
                # Skip first 16 bytes of payload (XTC header remainder) for tree walking
                actual_payload = payload[16:] if len(payload) > 16 else b''
                tree = walk_xtc_tree(actual_payload, max_level=5)
                for level, xtc, data in tree:
                    type_id = xtc.contains.type_id
                    
                    # Collect metadata
                    typeids[type_id]['count'] += 1
                    typeids[type_id]['sources'].add(f"0x{xtc.src.log:08x}:0x{xtc.src.phy:08x}")
                    typeids[type_id]['extents'].append(xtc.extent)
                    typeids[type_id]['damage_flags'].add(xtc.damage.value)
                
                # Don't scan entire huge file - first 10 events should show all types
                if event_count >= 10:
                    break
                    
        print(f"  Processed {event_count} events")
        
    except Exception as e:
        print(f"  Error scanning {filename}: {e}")
        return {}
    
    return dict(typeids)

def analyze_typeids(all_typeids):
    """Analyze collected TypeIds to identify potential Epix detectors"""
    
    print("\n" + "="*80)
    print("TYPEID ANALYSIS RESULTS")
    print("="*80)
    
    # Sort by TypeId value for easier reading
    sorted_typeids = sorted(all_typeids.items())
    
    print(f"\nFound {len(sorted_typeids)} unique TypeId values:\n")
    
    for type_id, info in sorted_typeids:
        # Convert sets to lists for display
        sources = sorted(list(info['sources']))
        damage_flags = sorted(list(info['damage_flags']))
        extent_range = f"{min(info['extents'])}-{max(info['extents'])}" if info['extents'] else "N/A"
        
        print(f"TypeId {type_id:3d} (0x{type_id:02x}):")
        print(f"  Count: {info['count']}")
        print(f"  Sources: {sources[:3]}{'...' if len(sources) > 3 else ''}")
        print(f"  Extent range: {extent_range} bytes")
        print(f"  Damage flags: {[f'0x{d:08x}' for d in damage_flags[:3]]}")
        print()
    
    # Look for potential Epix detectors based on patterns
    print("POTENTIAL EPIX DETECTORS:")
    print("-" * 40)
    
    epix_candidates = []
    for type_id, info in sorted_typeids:
        # Look for patterns that might indicate Epix detectors:
        # - Large extents (detector data is big)
        # - Consistent sizes (regular detector frames)
        # - Multiple occurrences (data from detector)
        
        if info['extents']:
            max_extent = max(info['extents'])
            min_extent = min(info['extents'])
            
            # Epix10ka2M frame would be: 4 + 16*352*384*2 = ~4.3MB
            # Plus calibration rows and environmental data
            expected_epix_size = 4 + 16 * 352 * 384 * 2  # ~4.3MB
            
            if max_extent > 1000000:  # > 1MB suggests detector data
                epix_candidates.append((type_id, info, max_extent))
                print(f"TypeId {type_id:3d}: Large data ({max_extent:,} bytes) - potential detector")
    
    if epix_candidates:
        print(f"\nFound {len(epix_candidates)} potential detector TypeIds")
    else:
        print("\nNo obvious large detector TypeIds found")
        print("This might mean:")
        print("- Epix data is compressed or structured differently")
        print("- Need to scan more events or different files")
        print("- Epix detector wasn't active in these events")

def main():
    """Main scanning function"""
    # XTC files for mfx100903824 run 105 - start with just one file
    xtc_files = [
        '/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s00-c00.xtc'
    ]
    
    print("Epix TypeId Discovery Script")
    print("="*50)
    
    # Verify files exist
    available_files = []
    for f in xtc_files:
        if Path(f).exists():
            available_files.append(f)
        else:
            print(f"File not found: {f}")
    
    if not available_files:
        print("No XTC files found! Please check file paths.")
        return
    
    print(f"Found {len(available_files)} XTC files to scan")
    
    # Collect TypeIds from all files
    all_typeids = defaultdict(lambda: {
        'count': 0, 
        'sources': set(), 
        'extents': [], 
        'damage_flags': set()
    })
    
    for filename in available_files:
        file_typeids = scan_file_for_typeids(filename)
        
        # Merge results
        for type_id, info in file_typeids.items():
            all_typeids[type_id]['count'] += info['count']
            all_typeids[type_id]['sources'].update(info['sources'])
            all_typeids[type_id]['extents'].extend(info['extents'])
            all_typeids[type_id]['damage_flags'].update(info['damage_flags'])
    
    # Analyze results
    analyze_typeids(all_typeids)
    
    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("1. Identify which TypeIds correspond to Epix detectors")
    print("2. Cross-reference with psana TypeId constants")
    print("3. Update binary_format.py with correct values")
    print("="*80)

if __name__ == "__main__":
    main()