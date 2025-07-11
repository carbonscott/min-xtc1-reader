#!/usr/bin/env python3
"""
Example usage of the XTC1 Reader package.

This demonstrates basic functionality for reading XTC files.
"""

import numpy as np
from xtc1reader import XTCReader, get_xtc_info, walk_xtc_tree
from xtc1reader.data_types import parse_detector_data, is_image_type, get_type_description
from xtc1reader.test_reader import create_test_xtc_file
import os
import tempfile


def example_basic_reading():
    """Example: Basic XTC file reading"""
    print("=== Example: Basic XTC File Reading ===")
    
    # Create a test XTC file for demonstration
    test_file = create_test_xtc_file()
    
    try:
        # Read the file
        with XTCReader(test_file) as reader:
            for i, (dgram, payload) in enumerate(reader):
                print(f"Event {i}:")
                print(f"  Timestamp: {dgram.seq.clock.as_double():.6f} seconds")
                print(f"  Fiducials: {dgram.seq.stamp.fiducials}")
                print(f"  Data type: {get_type_description(dgram.xtc.contains.type_id)}")
                print(f"  Payload size: {len(payload)} bytes")
                
                if dgram.xtc.damage.flags:
                    print(f"  ⚠️  Damage flags: 0x{dgram.xtc.damage.flags:06x}")
                else:
                    print(f"  ✓ No damage detected")
                print()
    
    finally:
        os.unlink(test_file)


def example_file_info():
    """Example: Get file information"""
    print("=== Example: File Information ===")
    
    test_file = create_test_xtc_file()
    
    try:
        info = get_xtc_info(test_file, max_events=10)
        
        print(f"File: {os.path.basename(info['filename'])}")
        print(f"Size: {info['file_size']} bytes")
        print(f"Events analyzed: {info['events_analyzed']}")
        
        if info['type_counts']:
            print("Data types found:")
            for type_name, count in info['type_counts'].items():
                print(f"  {type_name}: {count}")
        
        print()
    
    finally:
        os.unlink(test_file)


def example_xtc_tree_walking():
    """Example: Walking XTC tree structure"""
    print("=== Example: XTC Tree Structure ===")
    
    test_file = create_test_xtc_file()
    
    try:
        with XTCReader(test_file) as reader:
            for i, (dgram, payload) in enumerate(reader):
                print(f"Event {i} XTC structure:")
                
                # Walk the XTC tree
                tree = walk_xtc_tree(payload[16:], max_level=3)  # Skip XTC header remainder
                
                if tree:
                    for level, xtc, data in tree:
                        indent = "  " * (level + 1)
                        type_name = get_type_description(xtc.contains.type_id)
                        print(f"{indent}{type_name} v{xtc.contains.version} "
                              f"({xtc.extent} bytes)")
                else:
                    print("  (No nested containers)")
                
                print()
                break  # Just show first event
    
    finally:
        os.unlink(test_file)


def example_detector_data():
    """Example: Processing detector data"""
    print("=== Example: Detector Data Processing ===")
    
    # For this example, we'll simulate some detector data
    print("Note: This example shows the structure for processing real detector data.")
    print("In a real XTC file, you would iterate through events and find detector")
    print("data using the type IDs. Here's how you would process it:")
    print()
    
    # Example code structure (would work with real XTC files)
    example_code = '''
# Real usage with detector data:
with XTCReader('real_data.xtc') as reader:
    for dgram, payload in reader:
        tree = walk_xtc_tree(payload[16:])
        
        for level, xtc, data in tree:
            if is_image_type(xtc.contains.type_id):
                # Parse detector data
                detector_data = parse_detector_data(
                    data, xtc.contains.type_id, xtc.contains.version
                )
                
                if hasattr(detector_data, 'data'):
                    image = detector_data.data  # NumPy array
                    print(f"Got {detector_data.__class__.__name__} "
                          f"image: {image.shape}")
                    
                    # Process the image...
                    # E.g., apply calibrations, find peaks, etc.
    '''
    
    print(example_code)


def main():
    """Run all examples"""
    print("XTC1 Reader Package Examples")
    print("=" * 40)
    print()
    
    example_basic_reading()
    example_file_info()
    example_xtc_tree_walking()
    example_detector_data()
    
    print("=== Summary ===")
    print("✅ XTC1 Reader package is working correctly!")
    print("📖 Check README.md for more detailed usage information")
    print("🔧 Use 'xtc1reader --help' for command-line options")


if __name__ == "__main__":
    main()