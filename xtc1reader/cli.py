"""
Command-line interface for XTC reader.

Provides utilities to inspect and analyze XTC files.
"""

import argparse
import sys
import time
import numpy as np
from .xtc_reader import XTCReader, get_xtc_info, print_xtc_tree
from .data_types import parse_detector_data, is_image_type, get_type_description
from .binary_format import TypeId, transition_name
from .geometry import create_cspad_geometry, create_pnccd_geometry, create_camera_geometry, compute_detector_coordinates
from .epix_utils import get_detector_info, assemble_epix10ka2m_image, get_psana_geometry_info, assemble_epix10ka2m_psana_compatible

def get_clean_detector_name(type_id: int) -> str:
    """Get a clean, short detector name for filenames"""
    name_map = {
        TypeId.Id_Frame: "camera",
        TypeId.Id_pnCCDframe: "pnccd", 
        TypeId.Id_CspadElement: "cspad",
        TypeId.Id_PrincetonFrame: "princeton",
        TypeId.Id_Epix10kaArray: "epix10ka2m",
        TypeId.Id_Experimental_6193: "epix10ka2m",
        TypeId.Id_Experimental_117: "epix10ka2m", 
        TypeId.Id_Experimental_118: "epix10ka2m",
    }
    return name_map.get(type_id, f"type_{type_id}")
from .geometry_parser import load_default_epix10ka2m_geometry, print_geometry_summary
from .calibration import CalibrationManager, create_default_calibration, calibrate_detector_data


def info_command(filename: str, max_events: int = 100):
    """Print summary information about XTC file"""
    print(f"Analyzing XTC file: {filename}")
    print("=" * 50)
    
    try:
        info = get_xtc_info(filename, max_events=max_events)
        
        print(f"File size: {info['file_size']:,} bytes")
        print(f"Events analyzed: {info['events_analyzed']}")
        print()
        
        if info['type_counts']:
            print("Data types found:")
            for type_name, count in sorted(info['type_counts'].items()):
                print(f"  {type_name}: {count}")
            print()
        
        if info['damage_counts']:
            print("Damage flags found:")
            for damage, count in sorted(info['damage_counts'].items()):
                print(f"  {damage}: {count}")
            print()
            
    except Exception as e:
        print(f"Error analyzing file: {e}")
        return 1
    
    return 0


def dump_command(filename: str, max_events: int = 10, show_tree: bool = False):
    """Dump XTC file contents in human-readable format"""
    print(f"Dumping XTC file: {filename}")
    print("=" * 50)
    
    try:
        with XTCReader(filename) as reader:
            for i, (dgram, payload) in enumerate(reader):
                if i >= max_events:
                    break
                
                print(f"\nEvent {i}:")
                print(f"  Time: {dgram.seq.clock.as_double():.6f} seconds")
                print(f"  Fiducials: {dgram.seq.stamp.fiducials}")
                print(f"  Env: 0x{dgram.env.value:08x}")
                print(f"  XTC: {get_type_description(dgram.xtc.contains.type_id)} "
                      f"v{dgram.xtc.contains.version} "
                      f"({dgram.xtc.extent} bytes)")
                
                if dgram.xtc.damage.flags:
                    print(f"  Damage: 0x{dgram.xtc.damage.flags:06x}")
                
                if show_tree and len(payload) > 12:
                    print("  XTC Tree:")
                    print_xtc_tree(payload[12:])  # Skip first 12 bytes (rest of XTC header)
                
    except Exception as e:
        print(f"Error dumping file: {e}")
        return 1
    
    return 0


def extract_psana_style(exp: str, run: str, detector_name: str, output_dir: str = ".", max_events: int = 1000):
    """Extract detector data using psana-style experiment/run/detector specification"""
    import os
    import numpy as np
    from .detector_discovery import resolve_detector_from_psana_style
    from .epix_utils import assemble_epix10ka2m_image, assemble_epix10ka2m_psana_compatible
    
    print(f"Psana-style extraction:")
    print(f"  Experiment: {exp}")
    print(f"  Run: {run}")
    print(f"  Detector: {detector_name}")
    print(f"  Output directory: {output_dir}")
    
    # Resolve detector and XTC files using detector discovery
    detector_info, xtc_files = resolve_detector_from_psana_style(exp, run, detector_name)
    
    if not detector_info:
        print(f"❌ Detector '{detector_name}' not found for experiment {exp}")
        return 1
    
    if not xtc_files:
        print(f"❌ No XTC files found for experiment {exp}, run {run}")
        return 1
    
    print(f"✅ Found detector: {detector_info.detector_id}")
    print(f"✅ Found {len(xtc_files)} XTC files")
    print(f"✅ TypeId mappings: {detector_info.typeid_mappings}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Process first XTC file (or could iterate through all)
    return extract_command_with_detector_info(xtc_files[0], output_dir, detector_info, max_events)


def extract_command(filename: str, output_dir: str = ".", detector_type: str = None, max_events: int = 1000):
    """Extract detector data from XTC file (original direct file method)"""
    return extract_command_with_detector_info(filename, output_dir, None, max_events, detector_type)


def extract_command_with_detector_info(filename: str, output_dir: str, detector_info = None, max_events: int = 1000, detector_type: str = None):
    """Extract detector data from XTC file with optional detector info"""
    import os
    import numpy as np
    
    print(f"Extracting detector data from: {filename}")
    print(f"Output directory: {output_dir}")
    
    if detector_info:
        print(f"Using detector info: {detector_info.detector_id}")
        print(f"TypeId mappings: {detector_info.typeid_mappings}")
    elif detector_type:
        print(f"Filtering for detector type: {detector_type}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    extracted_count = 0
    
    try:
        with XTCReader(filename) as reader:
            for i, (dgram, payload) in enumerate(reader):
                if i >= max_events:
                    break
                
                # Walk through XTC tree looking for detector data
                from .xtc_reader import walk_xtc_tree
                # Skip first 16 bytes of payload (XTC header remainder) for tree walking
                actual_payload = payload[16:] if len(payload) > 16 else b''
                tree = walk_xtc_tree(actual_payload, max_level=5)
                
                for level, xtc, data in tree:
                    type_id = xtc.contains.type_id
                    
                    if is_image_type(type_id):
                        # Get clean detector name for filenames
                        detector_name = get_clean_detector_name(type_id)
                        
                        # Filter by detector type if specified
                        if detector_type and detector_type.lower() not in detector_name.lower():
                            continue
                        
                        try:
                            # Parse detector data
                            parsed_data = parse_detector_data(data, type_id, xtc.contains.version)
                            
                            if hasattr(parsed_data, 'data') and isinstance(parsed_data.data, np.ndarray):
                                # Save raw detector data
                                output_file = os.path.join(output_dir, 
                                    f"event_{i:04d}_{detector_name}_v{xtc.contains.version}_raw.npy")
                                np.save(output_file, parsed_data.data)
                                
                                print(f"Saved {detector_name} raw data: {output_file} "
                                      f"(shape: {parsed_data.data.shape})")
                                extracted_count += 1
                                
                            # Special handling for Epix10ka2M - save assembled images too
                            elif hasattr(parsed_data, 'frames') and isinstance(parsed_data.frames, np.ndarray):
                                # This is Epix10ka2M data - save raw frames
                                raw_file = os.path.join(output_dir, 
                                    f"event_{i:04d}_{detector_name}_v{xtc.contains.version}_raw.npy")
                                np.save(raw_file, parsed_data.frames)
                                print(f"Saved {detector_name} raw frames: {raw_file} "
                                      f"(shape: {parsed_data.frames.shape})")
                                
                                # Save simple assembly
                                try:
                                    simple_image = assemble_epix10ka2m_image(parsed_data.frames, include_gaps=False)
                                    simple_file = os.path.join(output_dir,
                                        f"event_{i:04d}_{detector_name}_v{xtc.contains.version}_simple.npy")
                                    np.save(simple_file, simple_image)
                                    print(f"Saved {detector_name} simple assembly: {simple_file} "
                                          f"(shape: {simple_image.shape})")
                                except Exception as e:
                                    print(f"Warning: Simple assembly failed: {e}")
                                
                                # Save psana-compatible assembly
                                try:
                                    psana_image = assemble_epix10ka2m_psana_compatible(parsed_data.frames)
                                    psana_file = os.path.join(output_dir,
                                        f"event_{i:04d}_{detector_name}_v{xtc.contains.version}_psana.npy")
                                    np.save(psana_file, psana_image)
                                    print(f"Saved {detector_name} psana assembly: {psana_file} "
                                          f"(shape: {psana_image.shape})")
                                except Exception as e:
                                    print(f"Warning: Psana assembly failed: {e}")
                                
                                extracted_count += 3  # Raw + simple + psana
                        
                        except Exception as e:
                            print(f"Warning: Failed to parse {detector_name} data in event {i}: {e}")
    
    except Exception as e:
        print(f"Error extracting data: {e}")
        return 1
    
    print(f"\nExtracted {extracted_count} detector images")
    return 0


def geometry_command(detector_type: str, output_file: str = None):
    """Generate and show detector geometry information"""
    print(f"Generating {detector_type} geometry...")
    
    try:
        # Create geometry based on detector type
        if detector_type.lower() == 'cspad':
            geometry = create_cspad_geometry()
        elif detector_type.lower() == 'pnccd':
            geometry = create_pnccd_geometry()
        elif detector_type.lower() == 'camera':
            geometry = create_camera_geometry()
        elif detector_type.lower() == 'epix10ka2m':
            # Handle Epix10ka2M detector info with both simple and psana-compatible geometry
            print("=== Simple Assembly Info ===")
            detector_info = get_detector_info()
            print(f"Detector: {detector_info['name']}")
            print(f"Number of panels: {detector_info['num_panels']}")
            print(f"Panels per quad: {detector_info['panels_per_quad']}")
            print(f"Panel shape: {detector_info['panel_shape']}")
            print(f"Pixel size: {detector_info['pixel_size_um']} μm")
            print(f"Total pixels: {detector_info['total_pixels']:,}")
            print(f"Assembled shape (no gaps): {detector_info['assembled_shape_no_gaps']}")
            print(f"Assembled shape (with gaps): {detector_info['assembled_shape_with_gaps']}")
            
            print("\n=== Psana-Compatible Assembly Info ===")
            try:
                # Load and display psana geometry
                geometry = load_default_epix10ka2m_geometry()
                print_geometry_summary(geometry)
                
                # Get psana assembly info
                psana_info = get_psana_geometry_info(geometry)
                print(f"\nPsana assembly info:")
                print(f"  Assembled image shape: {psana_info['assembled_image_shape']}")
                print(f"  Coordinate bounds:")
                bounds = psana_info['coordinate_bounds']
                print(f"    X: {bounds['x_min']:.0f} to {bounds['x_max']:.0f} μm ({bounds['x_range']:.0f} μm)")
                print(f"    Y: {bounds['y_min']:.0f} to {bounds['y_max']:.0f} μm ({bounds['y_range']:.0f} μm)")
                
            except Exception as e:
                print(f"Could not load psana geometry: {e}")
                print("Using basic geometry info only.")
            
            return 0
        else:
            print(f"Unknown detector type: {detector_type}")
            print("Supported types: cspad, pnccd, camera, epix10ka2m")
            return 1
        
        print(f"Detector: {geometry.name}")
        print(f"Number of segments: {geometry.num_segments}")
        print()
        
        # Show segment info
        for i, segment in enumerate(geometry.segments[:5]):  # Show first 5 segments
            print(f"Segment {i}:")
            print(f"  Shape: {segment.shape}")
            print(f"  Pixel size: {segment.pixel_size_um} μm")
            print(f"  Position: {segment.position_um} μm")
            print(f"  Rotation: {segment.rotation_deg}°")
            print()
        
        if len(geometry.segments) > 5:
            print(f"... and {len(geometry.segments) - 5} more segments")
            print()
        
        # Compute coordinates
        print("Computing detector coordinates...")
        coords = compute_detector_coordinates(geometry)
        print(f"Coordinate arrays shape: {coords.x_coords.shape}")
        print(f"X range: {coords.x_coords.min():.1f} to {coords.x_coords.max():.1f} μm")
        print(f"Y range: {coords.y_coords.min():.1f} to {coords.y_coords.max():.1f} μm")
        
        # Save coordinates if requested
        if output_file:
            import numpy as np
            np.savez(output_file,
                    x_coords=coords.x_coords,
                    y_coords=coords.y_coords,
                    z_coords=coords.z_coords)
            print(f"Coordinates saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating geometry: {e}")
        return 1


def calibration_command(action: str, detector_type: str = None, run_number: int = None,
                       calibration_dir: str = None, output_file: str = None):
    """Manage detector calibration constants and apply calibrations"""
    
    if action == "test":
        # Test calibration system
        print("Testing calibration system...")
        try:
            from .test_calibration import run_all_calibration_tests
            success = run_all_calibration_tests()
            return 0 if success else 1
        except Exception as e:
            print(f"Calibration tests failed: {e}")
            return 1
    
    elif action == "create-default":
        # Create default calibration for testing
        if not detector_type:
            print("Error: --detector-type required for create-default action")
            return 1
        
        if not run_number:
            run_number = 1
        
        print(f"Creating default calibration for {detector_type} run {run_number}...")
        
        # Determine detector shape based on type
        if detector_type.lower() == "cspad":
            shape = (32, 185, 388)  # 32 segments of 185x388
        elif detector_type.lower() == "pnccd":
            shape = (512, 512)
        elif detector_type.lower() == "camera":
            shape = (1024, 1024)
        elif detector_type.lower() == "epix10ka2m":
            shape = (16, 352, 384)  # 16 panels of 352x384
        else:
            print(f"Unknown detector type: {detector_type}")
            return 1
        
        constants = create_default_calibration(detector_type, shape, run_number)
        print(f"Created calibration constants:")
        print(f"  Detector: {constants.detector_name}")
        print(f"  Run: {constants.run_number}")
        print(f"  Pedestals shape: {constants.pedestals.shape}")
        print(f"  Pixel status shape: {constants.pixel_status.shape}")
        print(f"  Bad pixels: {np.sum(constants.pixel_status > 0)}")
        
        if output_file:
            np.savez(output_file,
                    detector_name=constants.detector_name,
                    run_number=constants.run_number,
                    pedestals=constants.pedestals,
                    pixel_status=constants.pixel_status,
                    common_mode=constants.common_mode)
            print(f"Saved to: {output_file}")
        
        return 0
    
    elif action == "info":
        # Show calibration information
        if not detector_type or not run_number:
            print("Error: --detector-type and --run-number required for info action")
            return 1
        
        print(f"Looking for calibration: {detector_type} run {run_number}")
        
        manager = CalibrationManager(calibration_dir)
        constants = manager.load_constants(detector_type, run_number)
        
        if constants is None:
            print("No calibration found")
            return 1
        
        print(f"Found calibration:")
        print(f"  Detector: {constants.detector_name}")
        print(f"  Run: {constants.run_number}")
        print(f"  Valid: {constants.is_valid()}")
        
        if constants.pedestals is not None:
            print(f"  Pedestals: {constants.pedestals.shape}, mean={np.mean(constants.pedestals):.1f}")
        
        if constants.has_pixel_status():
            bad_pixels = np.sum(constants.pixel_status > 0)
            total_pixels = np.prod(constants.pixel_status.shape)
            print(f"  Bad pixels: {bad_pixels}/{total_pixels} ({100*bad_pixels/total_pixels:.1f}%)")
        
        if constants.has_common_mode():
            regions = np.unique(constants.common_mode)
            print(f"  Common mode regions: {len(regions)}")
        
        return 0
    
    else:
        print(f"Unknown calibration action: {action}")
        print("Available actions: test, create-default, info")
        return 1


def test_command():
    """Run internal tests"""
    print("Running XTC reader tests...")
    
    # Try to import and run tests from the tests directory
    try:
        import sys
        import os
        
        # Add tests directory to path
        tests_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tests')
        if os.path.exists(tests_dir):
            sys.path.insert(0, tests_dir)
        
        from test_reader import run_all_tests
        success = run_all_tests()
        return 0 if success else 1
        
    except ImportError:
        print("Test modules not found. Please run tests manually:")
        print("  python tests/test_reader.py")
        print("  python tests/test_geometry.py") 
        print("  python tests/test_calibration.py")
        return 1


def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description="XTC1 Reader - Minimal LCLS1 XTC file reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xtc1reader info data.xtc                    # Show file summary  
  xtc1reader dump data.xtc --max-events 5    # Dump first 5 events
  xtc1reader extract data.xtc --detector cspad  # Extract CSPad images
  xtc1reader geometry cspad                   # Show CSPad geometry
  xtc1reader calibration test                 # Test calibration system
  xtc1reader test                             # Run tests
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show XTC file information')
    info_parser.add_argument('filename', help='XTC file to analyze')
    info_parser.add_argument('--max-events', type=int, default=100,
                           help='Maximum events to analyze (default: 100)')
    
    # Dump command
    dump_parser = subparsers.add_parser('dump', help='Dump XTC file contents')
    dump_parser.add_argument('filename', help='XTC file to dump')
    dump_parser.add_argument('--max-events', type=int, default=10,
                           help='Maximum events to dump (default: 10)')
    dump_parser.add_argument('--tree', action='store_true',
                           help='Show XTC tree structure')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract detector data')
    extract_parser.add_argument('filename', help='XTC file to extract from')
    extract_parser.add_argument('--output-dir', default='.',
                               help='Output directory (default: current)')
    extract_parser.add_argument('--detector', 
                               help='Filter by detector type (e.g., cspad, pnccd)')
    extract_parser.add_argument('--max-events', type=int, default=1000,
                               help='Maximum events to process (default: 1000)')
    
    # Psana-style extract command
    psana_parser = subparsers.add_parser('extract-psana', help='Extract detector data using psana-style parameters')
    psana_parser.add_argument('experiment', help='Experiment name (e.g., mfx100903824)')
    psana_parser.add_argument('run', help='Run number (e.g., 105)')  
    psana_parser.add_argument('detector', help='Detector name (e.g., epix10k2M)')
    psana_parser.add_argument('--output-dir', default='.',
                             help='Output directory (default: current)')
    psana_parser.add_argument('--max-events', type=int, default=1000,
                             help='Maximum events to process (default: 1000)')
    
    # Geometry command
    geometry_parser = subparsers.add_parser('geometry', help='Generate detector geometry')
    geometry_parser.add_argument('detector_type', choices=['cspad', 'pnccd', 'camera', 'epix10ka2m'],
                                help='Detector type to generate geometry for')
    geometry_parser.add_argument('--output', '-o', help='Save coordinates to file (.npz format)')
    
    # Calibration command
    calibration_parser = subparsers.add_parser('calibration', help='Manage detector calibration')
    calibration_parser.add_argument('action', choices=['test', 'create-default', 'info'],
                                   help='Calibration action to perform')
    calibration_parser.add_argument('--detector-type', choices=['cspad', 'pnccd', 'camera', 'epix10ka2m'],
                                   help='Detector type')
    calibration_parser.add_argument('--run-number', type=int, help='Run number')
    calibration_parser.add_argument('--calibration-dir', help='Calibration directory')
    calibration_parser.add_argument('--output', '-o', help='Output file for calibration data')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run internal tests')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to command functions
    if args.command == 'info':
        return info_command(args.filename, args.max_events)
    
    elif args.command == 'dump':
        return dump_command(args.filename, args.max_events, args.tree)
    
    elif args.command == 'extract':
        return extract_command(args.filename, args.output_dir, args.detector, args.max_events)
    
    elif args.command == 'extract-psana':
        return extract_psana_style(args.experiment, args.run, args.detector, args.output_dir, args.max_events)
    
    elif args.command == 'geometry':
        return geometry_command(args.detector_type, args.output)
    
    elif args.command == 'calibration':
        return calibration_command(args.action, args.detector_type, args.run_number,
                                 args.calibration_dir, args.output)
    
    elif args.command == 'test':
        return test_command()
    
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())