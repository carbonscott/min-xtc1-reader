#!/usr/bin/env python3
"""
Test script for validating XTC1 reader against real LCLS data.

This script performs comprehensive testing of the XTC1 reader using real
XTC files from the LCLS data archive.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback

# Set up environment
os.environ['SIT_PSDM_DATA'] = '/sdf/data/lcls/ds'

from xtc1reader import (
    XTCReader, get_xtc_info, 
    CalibrationManager, create_default_calibration,
    create_cspad_geometry, compute_detector_coordinates
)
from xtc1reader.data_types import parse_detector_data, is_image_type, get_type_description
from xtc1reader.binary_format import TypeId


class RealDataTester:
    """Comprehensive tester for real XTC data"""
    
    def __init__(self, xtc_file: str):
        """
        Initialize tester with real XTC file.
        
        Args:
            xtc_file: Path to real XTC file to test
        """
        self.xtc_file = Path(xtc_file)
        self.results = {
            'file_info': {},
            'detector_types': set(),
            'events_processed': 0,
            'errors': [],
            'warnings': [],
            'performance': {}
        }
        
        if not self.xtc_file.exists():
            raise FileNotFoundError(f"XTC file not found: {xtc_file}")
        
        print(f"Testing XTC1 reader with real file: {self.xtc_file}")
        print(f"File size: {self.xtc_file.stat().st_size / 1024**2:.1f} MB")
        print()
    
    def test_file_info(self) -> bool:
        """Test basic file information extraction"""
        print("=" * 60)
        print("TEST 1: File Information Extraction")
        print("=" * 60)
        
        try:
            start_time = time.time()
            info = get_xtc_info(str(self.xtc_file), max_events=50)
            elapsed = time.time() - start_time
            
            self.results['file_info'] = info
            self.results['performance']['info_extraction'] = elapsed
            
            print(f"✅ File info extracted in {elapsed:.3f}s")
            print(f"File size: {info['file_size']:,} bytes")
            print(f"Events analyzed: {info['events_analyzed']}")
            
            if info['type_counts']:
                print("Data types found:")
                for type_name, count in sorted(info['type_counts'].items()):
                    print(f"  {type_name}: {count}")
                    self.results['detector_types'].add(type_name)
            
            if info['damage_counts']:
                print("Damage flags found:")
                for damage, count in sorted(info['damage_counts'].items()):
                    print(f"  {damage}: {count}")
            
            print()
            return True
            
        except Exception as e:
            error_msg = f"File info extraction failed: {e}"
            print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            traceback.print_exc()
            return False
    
    def test_event_iteration(self, max_events: int = 20) -> bool:
        """Test event-by-event iteration"""
        print("=" * 60)
        print("TEST 2: Event Iteration")
        print("=" * 60)
        
        try:
            start_time = time.time()
            event_count = 0
            detector_data_count = 0
            transition_types = set()
            
            with XTCReader(str(self.xtc_file)) as reader:
                for dgram, payload in reader:
                    event_count += 1
                    
                    # Record transition type
                    transition_types.add(dgram.seq.service)
                    
                    # Check for detector data in payload
                    if payload and len(payload) > 0:
                        detector_data_count += 1
                        
                        # Try to parse detector data
                        if event_count <= 3:  # Detail for first few events
                            print(f"Event {event_count}:")
                            print(f"  Timestamp: {dgram.seq.clock.as_double():.6f}s")
                            print(f"  Transition: {dgram.seq.service}")
                            print(f"  Payload size: {len(payload)} bytes")
                            
                            # Try to extract detector information
                            if hasattr(dgram, 'xtc') and dgram.xtc:
                                try:
                                    # Basic XTC inspection
                                    print(f"  XTC type: {dgram.xtc.type_id}")
                                    print(f"  XTC source: {dgram.xtc.src}")
                                except:
                                    pass
                            print()
                    
                    if event_count >= max_events:
                        break
            
            elapsed = time.time() - start_time
            self.results['events_processed'] = event_count
            self.results['performance']['event_iteration'] = elapsed
            
            print(f"✅ Processed {event_count} events in {elapsed:.3f}s")
            print(f"Events with detector data: {detector_data_count}")
            print(f"Transition types: {sorted(transition_types)}")
            print(f"Processing rate: {event_count/elapsed:.1f} events/second")
            print()
            return True
            
        except Exception as e:
            error_msg = f"Event iteration failed: {e}"
            print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            traceback.print_exc()
            return False
    
    def test_detector_data_extraction(self, max_events: int = 10) -> bool:
        """Test detector data extraction and parsing"""
        print("=" * 60)
        print("TEST 3: Detector Data Extraction")
        print("=" * 60)
        
        try:
            detector_samples = {}
            event_count = 0
            
            with XTCReader(str(self.xtc_file)) as reader:
                for dgram, payload in reader:
                    event_count += 1
                    
                    if payload and len(payload) > 0:
                        # Try to parse detector data
                        try:
                            parsed_data = parse_detector_data(payload, dgram.xtc.type_id)
                            if parsed_data is not None:
                                type_desc = get_type_description(dgram.xtc.type_id)
                                
                                if type_desc not in detector_samples:
                                    detector_samples[type_desc] = {
                                        'count': 0,
                                        'sample_data': parsed_data,
                                        'shape': getattr(parsed_data, 'shape', None) if hasattr(parsed_data, 'shape') else None,
                                        'type': type(parsed_data).__name__
                                    }
                                
                                detector_samples[type_desc]['count'] += 1
                                
                        except Exception as parse_error:
                            if event_count <= 5:  # Only show first few parse errors
                                print(f"  Parse error in event {event_count}: {parse_error}")
                    
                    if event_count >= max_events:
                        break
            
            print(f"✅ Extracted detector data from {event_count} events")
            
            if detector_samples:
                print("Detector data types found:")
                for det_type, info in detector_samples.items():
                    print(f"  {det_type}:")
                    print(f"    Count: {info['count']}")
                    print(f"    Data type: {info['type']}")
                    if info['shape']:
                        print(f"    Shape: {info['shape']}")
                    print()
            else:
                print("⚠️  No parseable detector data found")
                self.results['warnings'].append("No parseable detector data found")
            
            return True
            
        except Exception as e:
            error_msg = f"Detector data extraction failed: {e}"
            print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            traceback.print_exc()
            return False
    
    def test_calibration_system(self) -> bool:
        """Test calibration system with real calibration directories"""
        print("=" * 60)
        print("TEST 4: Calibration System")
        print("=" * 60)
        
        try:
            # Test calibration discovery in various locations
            calib_locations = [
                "/sdf/data/lcls/ds/*/calib",
                "/sdf/data/lcls/ds/mec/*/calib", 
                "/sdf/data/lcls/ds/cxi/*/calib",
                "/sdf/data/lcls/ds/xpp/*/calib"
            ]
            
            calibrations_found = []
            
            for location in calib_locations:
                try:
                    # Try to find calibration directories
                    from glob import glob
                    matching_dirs = glob(location)
                    
                    for calib_dir in matching_dirs[:3]:  # Test first 3 matches
                        if os.path.exists(calib_dir):
                            manager = CalibrationManager(calib_dir)
                            
                            # Test common detector types
                            for detector in ['cspad', 'pnccd', 'epix100a', 'jungfrau']:
                                for run_num in [1, 100, 1000]:
                                    constants = manager.load_constants(detector, run_num)
                                    if constants and constants.is_valid():
                                        calibrations_found.append({
                                            'detector': detector,
                                            'run': run_num,
                                            'directory': calib_dir,
                                            'has_pixel_status': constants.has_pixel_status(),
                                            'has_common_mode': constants.has_common_mode()
                                        })
                                        break  # Found one, move to next detector
                                
                except Exception as search_error:
                    continue  # Skip problematic directories
            
            if calibrations_found:
                print(f"✅ Found {len(calibrations_found)} calibrations:")
                for calib in calibrations_found:
                    print(f"  {calib['detector']} run {calib['run']} in {calib['directory']}")
                    print(f"    Pixel status: {calib['has_pixel_status']}")
                    print(f"    Common mode: {calib['has_common_mode']}")
            else:
                print("⚠️  No accessible calibrations found, testing default calibration")
                
                # Test default calibration creation
                test_constants = create_default_calibration("test_detector", (100, 100), 1)
                if test_constants.is_valid():
                    print("✅ Default calibration creation works")
                else:
                    print("❌ Default calibration creation failed")
            
            print()
            return True
            
        except Exception as e:
            error_msg = f"Calibration system test failed: {e}"
            print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            traceback.print_exc()
            return False
    
    def test_geometry_system(self) -> bool:
        """Test geometry system"""
        print("=" * 60)
        print("TEST 5: Geometry System")
        print("=" * 60)
        
        try:
            # Test standard geometries
            geometries = {
                'CSPad': create_cspad_geometry,
                # Add others as available
            }
            
            for geom_name, geom_func in geometries.items():
                try:
                    geom = geom_func()
                    coords = compute_detector_coordinates(geom)
                    
                    print(f"✅ {geom_name} geometry:")
                    print(f"  Segments: {geom.num_segments}")
                    print(f"  Coordinate shape: {coords.x_coords.shape}")
                    print(f"  X range: {coords.x_coords.min():.1f} to {coords.x_coords.max():.1f} μm")
                    print(f"  Y range: {coords.y_coords.min():.1f} to {coords.y_coords.max():.1f} μm")
                    print()
                    
                except Exception as geom_error:
                    print(f"❌ {geom_name} geometry failed: {geom_error}")
            
            return True
            
        except Exception as e:
            error_msg = f"Geometry system test failed: {e}"
            print(f"❌ {error_msg}")
            self.results['errors'].append(error_msg)
            traceback.print_exc()
            return False
    
    def run_all_tests(self) -> bool:
        """Run complete test suite"""
        print("🎯 REAL DATA VALIDATION TEST SUITE")
        print("=" * 80)
        print(f"File: {self.xtc_file}")
        print(f"Size: {self.xtc_file.stat().st_size / 1024**2:.1f} MB")
        print("=" * 80)
        print()
        
        tests = [
            self.test_file_info,
            self.test_event_iteration,
            self.test_detector_data_extraction,
            self.test_calibration_system,
            self.test_geometry_system
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Tests passed: {passed}/{total}")
        print(f"Events processed: {self.results['events_processed']}")
        print(f"Detector types found: {len(self.results['detector_types'])}")
        
        if self.results['detector_types']:
            print(f"Types: {', '.join(sorted(self.results['detector_types']))}")
        
        if self.results['errors']:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"  ❌ {error}")
        
        if self.results['warnings']:
            print(f"\nWarnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"  ⚠️  {warning}")
        
        if 'performance' in self.results:
            print(f"\nPerformance:")
            for metric, value in self.results['performance'].items():
                print(f"  {metric}: {value:.3f}s")
        
        print()
        success = passed == total and len(self.results['errors']) == 0
        if success:
            print("🎉 ALL TESTS PASSED! XTC1 reader works with real data!")
        else:
            print("⚠️  Some tests failed or had issues. Check errors above.")
        
        return success


def main():
    """Main test execution"""
    
    # Default test files (if accessible)
    default_test_files = [
        "/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc",
        "/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/smalldata/rte01-r0012-c03-c00.smd.xtc"
    ]
    
    # Get test file from command line or use default
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        # Try to find an accessible test file
        test_file = None
        for file_path in default_test_files:
            if os.path.exists(file_path):
                test_file = file_path
                print(f"Using default test file: {test_file}")
                break
        
        if not test_file:
            print("No test file specified and no default files accessible.")
            print("Usage: python test_real_data.py <path_to_xtc_file>")
            print("\nDefault test files to try:")
            for file_path in default_test_files:
                print(f"  {file_path}")
            return 1
    
    try:
        tester = RealDataTester(test_file)
        success = tester.run_all_tests()
        return 0 if success else 1
        
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())