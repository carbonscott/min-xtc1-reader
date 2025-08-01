# min-xtc1-reader

A minimal, lightweight Python library for reading LCLS1 XTC files without the full psana framework. Provides essential functionality for XTC file parsing, detector geometry, and basic calibration.

## Features

- **Pure Python**: No C++ dependencies, works with just NumPy
- **Lightweight**: Minimal implementation focused on essential functionality
- **Complete XTC Parsing**: Full support for LCLS1 XTC file format
- **Detector Geometry**: Coordinate mapping for CSPad, pnCCD, cameras, and **Epix10ka2M**
- **Psana-Compatible Assembly**: Sophisticated coordinate-based image assembly for Epix10ka2M detectors
- **Basic Calibration**: Pedestal subtraction, common mode correction, pixel masking
- **Command Line Interface**: Easy-to-use CLI for file inspection and analysis
- **Well Tested**: Comprehensive test suite with real data validation

## Installation

### From Source

```bash
git clone git@github.com:carbonscott/min-xtc1-reader.git
cd min-xtc1-reader
pip install -e .
```

### Dependencies

- Python 3.7+
- NumPy 1.19+

## Quick Start

### Reading XTC Files

```python
from xtc1reader import XTCReader

# Iterate through events in an XTC file
with XTCReader('data.xtc') as reader:
    for dgram, payload in reader:
        print(f"Event at {dgram.seq.clock.as_double():.6f}s")
        # Process detector data in payload
```

### Basic File Information

```python
from xtc1reader import get_xtc_info

# Get summary information about an XTC file
info = get_xtc_info('data.xtc', max_events=100)
print(f"File size: {info['file_size']:,} bytes")
print(f"Data types: {list(info['type_counts'].keys())}")
```

### Detector Geometry

```python
from xtc1reader.geometry import create_cspad_geometry, compute_detector_coordinates

# Create CSPad geometry and compute pixel coordinates
geometry = create_cspad_geometry()
coords = compute_detector_coordinates(geometry)

print(f"CSPad has {geometry.num_segments} segments")
print(f"Coordinate arrays shape: {coords.x_coords.shape}")
```

### Epix10ka2M Detector Support

```python
from xtc1reader import assemble_epix10ka2m_psana_compatible, parse_epix10ka2m_array
import numpy as np

# Parse Epix10ka2M detector data from XTC payload
epix_data = parse_epix10ka2m_array(raw_bytes, version=1)
print(f"Frame {epix_data.frame_number}: {epix_data.frames.shape}")

# Assemble into psana-compatible image (~1672×1674 pixels)
assembled_image = assemble_epix10ka2m_psana_compatible(epix_data.frames)
print(f"Assembled image: {assembled_image.shape}")

# Compare with simple assembly (704×3072 pixels)
from xtc1reader import assemble_epix10ka2m_image
simple_image = assemble_epix10ka2m_image(epix_data.frames, include_gaps=False)
print(f"Simple assembly: {simple_image.shape}")
```

### Calibration

```python
from xtc1reader.calibration import calibrate_detector_data
import numpy as np

# Apply calibration to detector data
raw_data = np.random.normal(1100, 20, (185, 388))  # Example raw data
calibrated = calibrate_detector_data(raw_data, 'cspad', run_number=123)
print(f"Applied calibration: {raw_data.shape} -> {calibrated.shape}")
```

## Command Line Interface

The package includes a comprehensive CLI for working with XTC files:

```bash
# Get file information
xtc1reader info data.xtc

# Dump first few events
xtc1reader dump data.xtc --max-events 5

# Extract detector data
xtc1reader extract data.xtc --detector cspad --max-events 100

# Show detector geometry
xtc1reader geometry cspad

# Show Epix10ka2M geometry (both simple and psana-compatible)
xtc1reader geometry epix10ka2m

# Test calibration system
xtc1reader calibration test

# Create default calibration for testing
xtc1reader calibration create-default --detector-type cspad --run-number 123

# Show help
xtc1reader --help
```

## API Overview

### Core Classes

- **`XTCReader`**: Main class for reading XTC files
- **`Datagram`**: Represents an XTC datagram (event header + payload)
- **`XTCContainer`**: Represents XTC data containers

### Geometry System

- **`DetectorGeometry`**: Multi-segment detector geometry
- **`DetectorSegment`**: Individual detector segment/chip
- **`CoordinateArrays`**: Pre-computed pixel coordinates

### Calibration System

- **`CalibrationManager`**: Loads calibration constants from files
- **`DetectorCalibrator`**: Applies calibrations to detector data
- **`CalibrationConstants`**: Container for calibration data

## Supported Detectors

- **CSPad**: Cornell-SLAC Pixel Array Detector
- **pnCCD**: p-n Charge-Coupled Device
- **Camera**: Various camera detectors (Opal, etc.)
- **Epix10ka2M**: Advanced pixel detector with sophisticated coordinate-based assembly

### Epix10ka2M Features

- **Psana-Compatible Assembly**: Produces ~1672×1674 images matching psana's `.image()` output
- **Coordinate-Based Geometry**: Handles panel rotations, translations, and tilts
- **Dual Assembly Modes**: Simple panel arrangement (704×3072) vs sophisticated coordinate assembly
- **Real Geometry Files**: Uses psana geometry definitions for accurate detector modeling
- **Wide Pixel Support**: Handles 250μm pixels at ASIC boundaries vs 100μm regular pixels

## Environment Variables

For LCLS environments, set:

```bash
export SIT_PSDM_DATA=/sdf/data/lcls/ds  # Path to LCLS data
```

## Examples

See the [`examples/`](examples/) directory for:

- [`example_usage.py`](examples/example_usage.py) - Basic usage examples
- [`test_real_data.py`](examples/test_real_data.py) - Real data validation script
- [`examples/README.md`](examples/README.md) - Detailed usage guide

## Documentation

- [`COMPREHENSIVE_LESSONS_LEARNED.md`](COMPREHENSIVE_LESSONS_LEARNED.md) - Complete technical guide and lessons learned
- [`docs/IMPLEMENTATION_SUMMARY.md`](docs/IMPLEMENTATION_SUMMARY.md) - Technical implementation details
- [`docs/REAL_DATA_TEST_PLAN.md`](docs/REAL_DATA_TEST_PLAN.md) - Testing with real LCLS data
- [`docs/DEVELOPMENT_PROGRESS.md`](docs/DEVELOPMENT_PROGRESS.md) - Development history

### Epix10ka2M Technical Details

The Epix10ka2M implementation includes:
- **16-panel detector**: 352×384 pixels per panel with individual rotations (0°, 90°, 180°, 270°)
- **Coordinate transformations**: 3D rotations, translations, and tilt corrections
- **Psana geometry compatibility**: Uses same geometry files and algorithms as psana framework
- **Binary data parsing**: Direct XTC payload parsing for Epix10ka2M ArrayV1 data
- **Image assembly**: Coordinate-to-pixel mapping with half-pixel boundary corrections

## Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m pytest tests/test_reader.py
python -m pytest tests/test_geometry.py
python -m pytest tests/test_calibration.py

# Or use the old-style test runners
python -m xtc1reader.test_reader
python -m xtc1reader.test_geometry  
python -m xtc1reader.test_calibration
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python -m pytest tests/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- LCLS team for XTC format specification and reference implementations
- SLAC National Accelerator Laboratory
- The psana framework developers for reference implementations

## Citation

If you use this software in your research, please cite:

```
xtc1reader: Minimal LCLS1 XTC file reader
https://github.com/carbonscott/min-xtc1-reader
```

## Support

- Report issues: [GitHub Issues](https://github.com/carbonscott/min-xtc1-reader/issues)
- Documentation: [README](README.md) and [`docs/`](docs/) directory
- Examples: [`examples/`](examples/) directory

---

**Note**: This is a minimal implementation focused on essential XTC reading functionality. For full-featured LCLS data analysis, consider using the complete [psana framework](https://github.com/lcls-psana/psana).