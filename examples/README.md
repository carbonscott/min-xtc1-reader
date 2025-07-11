# Examples

This directory contains usage examples and demonstrations for the xtc1reader package.

## Files

### [`example_usage.py`](example_usage.py)
Basic usage examples demonstrating core functionality:
- Reading XTC files with `XTCReader`
- Getting file information with `get_xtc_info`
- Using the geometry system
- Applying calibrations
- Command-line interface examples

```bash
python examples/example_usage.py
```

### [`test_real_data.py`](test_real_data.py)
Comprehensive test script for validating the XTC1 reader against real LCLS data:
- File structure validation
- Event iteration testing
- Detector data extraction
- Calibration system testing
- Performance benchmarking

```bash
# Test with default files (if available)
python examples/test_real_data.py

# Test with specific XTC file
python examples/test_real_data.py /path/to/your/data.xtc
```

## Usage Patterns

### Basic File Reading

```python
from xtc1reader import XTCReader

with XTCReader('data.xtc') as reader:
    for dgram, payload in reader:
        print(f"Event: {dgram.seq.clock.as_double():.6f}s")
        if payload:
            print(f"  Payload size: {len(payload)} bytes")
```

### Detector Data Processing

```python
from xtc1reader import XTCReader
from xtc1reader.data_types import parse_detector_data
from xtc1reader.calibration import calibrate_detector_data

with XTCReader('data.xtc') as reader:
    for dgram, payload in reader:
        if payload:
            # Parse detector data
            data = parse_detector_data(payload, dgram.xtc.type_id)
            
            if data is not None:
                # Apply calibration
                calibrated = calibrate_detector_data(
                    data, 'cspad', dgram.seq.service
                )
                
                print(f"Calibrated data shape: {calibrated.shape}")
```

### Geometry and Coordinates

```python
from xtc1reader.geometry import (
    create_cspad_geometry, 
    compute_detector_coordinates
)

# Create detector geometry
geometry = create_cspad_geometry()

# Compute pixel coordinates
coords = compute_detector_coordinates(geometry)

print(f"Detector has {geometry.num_segments} segments")
print(f"X coordinates range: {coords.x_coords.min():.1f} to {coords.x_coords.max():.1f} μm")
print(f"Y coordinates range: {coords.y_coords.min():.1f} to {coords.y_coords.max():.1f} μm")
```

### Command Line Interface

```bash
# Get file information
xtc1reader info /path/to/data.xtc

# Dump first 3 events
xtc1reader dump /path/to/data.xtc --max-events 3

# Extract CSPad data
xtc1reader extract /path/to/data.xtc --detector cspad

# Show CSPad geometry
xtc1reader geometry cspad

# Test calibration system
xtc1reader calibration test

# Create default calibration
xtc1reader calibration create-default --detector-type cspad --run-number 100
```

## Environment Setup

For LCLS environments:

```bash
export SIT_PSDM_DATA=/sdf/data/lcls/ds
```

## Testing with Real Data

The `test_real_data.py` script provides comprehensive validation against real LCLS XTC files. It tests:

1. **File Information Extraction** - Basic file parsing and metadata
2. **Event Iteration** - Sequential reading through events
3. **Detector Data Extraction** - Parsing of detector-specific data
4. **Calibration System** - Loading and applying calibrations
5. **Geometry System** - Coordinate mapping functionality

Example output:
```
🎯 REAL DATA VALIDATION TEST SUITE
================================================================================
File: /path/to/real_data.xtc
Size: 150.2 MB
================================================================================

✅ File info extracted in 0.234s
✅ Processed 50 events in 1.456s
✅ Found detector data types: ['cspad', 'camera']
✅ Calibration system functional
✅ Geometry system functional

🎉 ALL TESTS PASSED! XTC1 reader works with real data!
```

## Error Handling

The examples include robust error handling for common issues:

- **File not found**: Clear error messages
- **Corrupted data**: Graceful degradation
- **Missing calibrations**: Fallback to defaults
- **Unsupported detectors**: Informative warnings

## Performance Notes

- **Memory usage**: Examples show efficient streaming reading
- **Processing speed**: Typical rates of 100-1000 events/second
- **Large files**: Uses iterative processing to handle multi-GB files

## Extending the Examples

To add your own analysis:

1. Copy `example_usage.py` as a starting point
2. Add your specific detector types or analysis logic
3. Use the existing error handling patterns
4. Test with both synthetic and real data

For questions or additional examples, please open an issue on the [GitHub repository](https://github.com/carbonscott/min-xtc1-reader).