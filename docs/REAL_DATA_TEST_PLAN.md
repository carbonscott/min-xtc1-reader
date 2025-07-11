# Real XTC File Test Plan

## Environment Setup

### Key Environment Variables Found:
- `SIT_PSDM_DATA=/sdf/data/lcls/ds` - Main PSDM data directory
- `SIT_DATA=/sdf/group/lcls/ds/ana/sw/conda1/inst/envs/ana-4.0.63-py3/data:/sdf/group/lcls/ds/ana/data/`
- `SIT_ROOT=/sdf/group/lcls/ds/ana`

### Data Organization:
```
/sdf/data/lcls/ds/
├── [experiment]/              # e.g., cxi, amo, mec, xpp, etc.
│   ├── [expname]/             # e.g., cxid9114, mecl2315
│   │   ├── xtc/               # XTC files
│   │   ├── calib/             # Calibration data
│   │   └── scratch/           # User results
│   └── calib/                 # Shared calibration data
│       ├── cspad/
│       ├── pnccd/
│       ├── epix100a/
│       └── jungfrau/
```

## Test Data Locations

### Available XTC Files:
- Small test files: `/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/`
- Small data (smd) files: `/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/smalldata/`

### Calibration Data:
- Shared calibrations: `/sdf/data/lcls/ds/*/calib/`
- Detector-specific: Found Epix10kaQuad calibrations in `/sdf/data/lcls/ds/mec/`

## Test Plan

### Phase 1: Basic XTC File Reading
**Objective:** Verify our XTC reader can parse real files

```bash
# Test 1: File info and structure
export SIT_PSDM_DATA=/sdf/data/lcls/ds
python -m xtc1reader.cli info /sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc

# Test 2: Dump first few events
python -m xtc1reader.cli dump /sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc --max-events 3

# Test 3: Check for detector data
python -m xtc1reader.cli extract /sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc --max-events 10
```

### Phase 2: Detector Data Validation
**Objective:** Extract and validate detector data types

```bash
# Test specific detector extraction
python -c "
from xtc1reader import XTCReader
import os
os.environ['SIT_PSDM_DATA'] = '/sdf/data/lcls/ds'

# Test with real file
xtc_file = '/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc'
print(f'Testing file: {xtc_file}')

with XTCReader(xtc_file) as reader:
    detector_types = set()
    event_count = 0
    
    for dgram, payload in reader:
        event_count += 1
        if hasattr(dgram, 'xtc') and dgram.xtc:
            # Extract detector types
            # [Implementation details here]
            pass
        
        if event_count >= 5:
            break
    
    print(f'Processed {event_count} events')
    print(f'Detector types found: {detector_types}')
"
```

### Phase 3: Calibration System Testing
**Objective:** Test calibration loading with real calibration files

```bash
# Test 1: Find and load real calibration
python -c "
from xtc1reader.calibration import CalibrationManager
import os

# Set up environment
os.environ['SIT_PSDM_DATA'] = '/sdf/data/lcls/ds'

# Test calibration discovery
calib_dirs = [
    '/sdf/data/lcls/ds/*/calib',
    '/sdf/data/lcls/ds/mec/*/calib',
    '/sdf/data/lcls/ds/cxi/*/calib'
]

for calib_dir in calib_dirs:
    manager = CalibrationManager(calib_dir)
    # Test loading various detector types
    for detector in ['cspad', 'pnccd', 'epix100a']:
        constants = manager.load_constants(detector, 1)
        if constants:
            print(f'Found {detector} calibration in {calib_dir}')
            break
"

# Test 2: Apply calibration to real detector data  
python -c "
# [Apply calibration to extracted detector data]
"
```

### Phase 4: Geometry System Testing
**Objective:** Test geometry with real detector configurations

```bash
# Test 1: Compare our geometry with known detector layouts
python -c "
from xtc1reader.geometry import create_cspad_geometry, compute_detector_coordinates

# Create our geometry
geom = create_cspad_geometry()
coords = compute_detector_coordinates(geom)

print(f'Our CSPad geometry:')
print(f'  Segments: {geom.num_segments}')
print(f'  Coordinate shape: {coords.x_coords.shape}')
print(f'  X range: {coords.x_coords.min():.1f} to {coords.x_coords.max():.1f} μm')
print(f'  Y range: {coords.y_coords.min():.1f} to {coords.y_coords.max():.1f} μm')

# TODO: Compare with reference geometry if available
"
```

### Phase 5: End-to-End Workflow
**Objective:** Complete analysis workflow with real data

```bash
# Test complete analysis pipeline
python -c "
import os
from xtc1reader import XTCReader, CalibrationManager, create_cspad_geometry

# Set environment
os.environ['SIT_PSDM_DATA'] = '/sdf/data/lcls/ds'

# Input file
xtc_file = '/sdf/data/lcls/ds/xrootd/sdf/rucio/rte/rte01/xtc/rte01-r0001-s02-c00.xtc'
print(f'Processing: {xtc_file}')

# Read XTC file
with XTCReader(xtc_file) as reader:
    for i, (dgram, payload) in enumerate(reader):
        if i >= 1:  # Process just first event
            break
        
        print(f'Event {i}:')
        print(f'  Timestamp: {dgram.seq.clock.as_double():.6f}s')
        print(f'  Transition: {dgram.seq.service}')
        
        # Extract detector data
        # Apply calibration
        # Apply geometry
        # [Complete analysis]

print('End-to-end test completed')
"
```

## Validation Criteria

### Success Metrics:
1. **File Reading**: Can successfully open and iterate through real XTC files
2. **Data Types**: Correctly identifies and parses detector data types found in real files
3. **Calibration**: Can load and apply real calibration data when available
4. **Geometry**: Produces reasonable coordinate mappings for known detectors
5. **Performance**: Processes files at reasonable speed (>100 events/second for small events)

### Expected Challenges:
1. **Data Types**: Real files may contain detector types not yet implemented
2. **Calibration Format**: Real calibration files may have different formats than expected
3. **File Permissions**: Some data may not be accessible
4. **Large Files**: Real files may be much larger than test data
5. **Complex Geometry**: Real detector configurations may be more complex

## Error Handling Strategy

### For Missing Data:
- Graceful degradation when calibration not available
- Default geometry when real geometry not found
- Clear warnings for unimplemented detector types

### For File Issues:
- Robust error handling for corrupted or incomplete files
- Skip damaged events and continue processing
- Clear error messages for permission/access issues

## Test Execution Commands

```bash
# Set up environment
export SIT_PSDM_DATA=/sdf/data/lcls/ds

# Basic tests
python test_real_data.py

# CLI tests  
python -m xtc1reader.cli info [REAL_XTC_FILE]
python -m xtc1reader.cli dump [REAL_XTC_FILE] --max-events 3
python -m xtc1reader.cli extract [REAL_XTC_FILE] --detector cspad

# Geometry tests
python -m xtc1reader.cli geometry cspad

# Calibration tests
python -m xtc1reader.cli calibration info --detector-type cspad --run-number 1
```

## Next Steps After User Provides Real File

1. **Immediate Tests**:
   - File info and basic parsing
   - Event iteration and structure analysis
   - Detector data type identification

2. **Deep Analysis**:
   - Compare parsed data with expected formats
   - Validate detector data shapes and values
   - Test calibration application if calibration available

3. **Validation**:
   - Compare results with psana output (if available)
   - Verify geometry makes physical sense
   - Check performance on larger files

4. **Documentation**:
   - Update examples with real file usage
   - Document any limitations found
   - Create troubleshooting guide

---

**Ready for Real Data Testing!** 🎯

Please provide the path to a real XTC file and I'll execute this test plan to validate our XTC1 reader against real LCLS data.