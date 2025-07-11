# XTC1 Reader

A minimal Python library for reading LCLS1 XTC files without the full psana framework.

## Features

- **Lightweight**: Pure Python with minimal dependencies (only NumPy required)
- **Fast**: Direct binary parsing of XTC format 
- **Simple**: Clean API for common use cases
- **Standalone**: No LCLS software environment required

## Installation

```bash
pip install xtc1reader
```

Or install from source:

```bash
git clone https://github.com/lcls/xtc1reader.git
cd xtc1reader
pip install -e .
```

## Quick Start

### Reading XTC Files

```python
from xtc1reader import XTCReader

# Iterate through events in an XTC file
with XTCReader('data.xtc') as reader:
    for dgram, payload in reader:
        print(f"Event at {dgram.seq.clock.as_double():.6f} seconds")
        print(f"Event ID: {dgram.seq.stamp.fiducials}")
        
        # Process detector data in payload...
```

### Analyzing File Contents

```python
from xtc1reader import get_xtc_info

# Get summary information
info = get_xtc_info('data.xtc', max_events=100)
print(f"File size: {info['file_size']:,} bytes")
print(f"Data types: {list(info['type_counts'].keys())}")
```

### Extracting Detector Data

```python
from xtc1reader import XTCReader, walk_xtc_tree
from xtc1reader.data_types import parse_detector_data, is_image_type

with XTCReader('data.xtc') as reader:
    for dgram, payload in reader:
        # Walk through nested XTC containers
        tree = walk_xtc_tree(payload[12:])  # Skip XTC header
        
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
```

## Command Line Interface

The package includes a command-line tool:

```bash
# Show file information
xtc1reader info data.xtc

# Dump event contents  
xtc1reader dump data.xtc --max-events 5 --tree

# Extract detector images
xtc1reader extract data.xtc --detector cspad --output-dir ./images/

# Run tests
xtc1reader test
```

## Supported Detectors

- **Camera detectors**: Generic frame format
- **CSPad**: 2x1 elements and full detector arrays  
- **pnCCD**: 512x512 pixel frames
- **Princeton**: CCD camera frames
- **More detectors**: Easy to add new parsers

## Data Format Details

### XTC File Structure

XTC files contain a sequence of **datagrams**, each with:
- **24-byte header**: Timestamp, environment, damage info
- **Variable payload**: Nested XTC containers with detector data

### Datagram Header (24 bytes)
- `Sequence` (16 bytes): ClockTime + TimeStamp  
- `Env` (4 bytes): Environment/run identifier
- `XTC damage` (4 bytes): First part of XTC container

### XTC Container (16 bytes)
- `Damage` (4 bytes): Data quality flags
- `Src` (8 bytes): Source identifier (detector/device)
- `TypeId` (4 bytes): Data type and version
- `Extent` (4 bytes): Total container size

## Advanced Usage

### Custom Data Parsers

```python
from xtc1reader.data_types import parse_detector_data
from xtc1reader.binary_format import TypeId

def parse_my_detector(data: bytes, version: int):
    # Custom parsing logic
    return MyDetectorData(...)

# Register custom parser
parse_detector_data.register(TypeId.Id_MyDetector, parse_my_detector)
```

### Low-Level Binary Access

```python
from xtc1reader.binary_format import parse_xtc_header, parse_datagram_header

# Parse binary structures directly
with open('data.xtc', 'rb') as f:
    header_bytes = f.read(24)
    dgram = parse_datagram_header(header_bytes)
    
    xtc_bytes = f.read(16) 
    xtc = parse_xtc_header(xtc_bytes)
```

## Architecture

The package is organized into focused modules:

- `binary_format.py`: Low-level XTC format parsing
- `xtc_reader.py`: File iteration and container parsing
- `data_types.py`: Detector-specific data parsers  
- `cli.py`: Command-line interface
- `test_reader.py`: Test suite

## Performance

Reading XTC files is I/O bound. Performance tips:

- Use file iteration instead of loading entire files
- Skip unused data types to reduce parsing overhead
- Consider parallel processing for multiple files

Typical performance: ~100-500 MB/s depending on data complexity and storage.

## Limitations

This is a **minimal** reader focused on essential functionality:

- ✅ Sequential file reading (no random access)
- ✅ Basic detector data types
- ✅ Essential XTC format support  
- ❌ No psana framework integration
- ❌ No advanced calibration algorithms
- ❌ No real-time data streams

For full LCLS analysis capabilities, use the complete psana framework.

## Contributing

Contributions welcome! Areas for improvement:

- Additional detector data parsers
- Geometry and calibration modules (Phase 2)
- Performance optimizations
- Better error handling
- More comprehensive tests

## License

MIT License - see LICENSE file for details.

## Credits

Developed by analyzing the LCLS1 legacy codebase to understand XTC binary formats and create a minimal, standalone implementation.

Built with ❤️ for the LCLS user community.