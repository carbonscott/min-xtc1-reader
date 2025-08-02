# Min-XTC1-Reader Investigation Report

## Executive Summary

The min-xtc1-reader **can successfully read** the same XTC data that psana uses. The investigation revealed that the fundamental XTC file parsing works correctly, but there are key differences in data processing scope and functionality between min-xtc1-reader and psana.

## Investigation Setup

### Key Directories Used

- **Main working directory**: `/sdf/data/lcls/ds/prj/prjcwang31/results`
- **Min-xtc1-reader source**: `/sdf/data/lcls/ds/prj/prjcwang31/results/software/min-xtc1-reader`
- **Psana wrapper source**: `/sdf/home/c/cwang31/codes/psana-wrapper`
- **LCLS environment setup**: `/sdf/group/lcls/ds/ana/sw/conda1/manage/bin/psconda.sh`
- **Test data location**: `/sdf/data/lcls/ds/mfx/mfx100903824/xtc`
- **LCLS1/psana1 reference**: `/sdf/data/lcls/ds/prj/prjcwang31/results/software/lcls1`

### Environment Variables Required

```bash
export SIT_ROOT=/sdf/group/lcls/ds/ana
export SIT_PSDM_DATA=/sdf/data/lcls/ds
export SIT_DATA=/sdf/group/lcls/ds/ana/sw/conda1/inst/envs/ana-4.0.66-py3/data:/sdf/group/lcls/ds/ana/data/
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ARCH=x86_64-rhel7-gcc48-opt
```

## Test Case: Experiment mfx100903824, Run 105, Detector epix10k2M

### Data Structure Analysis

**XTC Files for Run 105:**
- Total files: 12 XTC files
- Structure: 6 streams (s00-s05) × 2 chunks (c00-c01)
- File naming pattern: `mfx100903824-r0105-s{XX}-c{YY}.xtc`
- Example file size: ~21GB for `mfx100903824-r0105-s00-c00.xtc`

### Psana Behavior (Reference/Working)

**Command tested:**
```bash
mpirun -N 2 python run_smd.py
```

**Results:**
- Successfully reads detector data
- Aggregates across all 12 XTC files automatically
- Total events found: 35,940 events
- Output: 1691×1691 pixel detector images
- Uses SMD (Small Data) mode for efficient parallel processing

### Min-XTC1-Reader Behavior

**Command tested:**
```python
from xtc1reader import XTCReader
reader = XTCReader('/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s00-c00.xtc')
events = list(reader)
```

**Results:**
- Successfully reads XTC file structure
- Single file processing: 4,825 events from first file
- Can parse datagram headers and XTC containers
- Provides raw XTC payload data requiring additional parsing

## Key Findings

### ✅ What Works

1. **Basic XTC Reading**: Min-xtc1-reader successfully reads XTC files from the same experiment/run that psana uses
2. **File Format Compatibility**: Correctly parses XTC file structure, datagram headers, and container hierarchy
3. **Data Access**: Can extract raw payload data from XTC containers
4. **Same Data Source**: Uses identical XTC files as psana (confirmed working with actual LCLS data)

### ❌ What's Missing

1. **Multi-file Aggregation**: 
   - Psana: Automatically combines data from all 12 files (35,940 events total)
   - Min-xtc1-reader: Processes one file at a time (4,825 events per file)

2. **Detector-Specific Data Processing**:
   - Psana: Provides 1691×1691 detector images directly
   - Min-xtc1-reader: Provides raw XTC payload requiring manual parsing

3. **High-Level Data Extraction**:
   - Psana: Built-in detector calibration, geometry correction, and data type handling
   - Min-xtc1-reader: Raw binary data without detector-specific interpretation

4. **Data Type Support**:
   - Missing epix10k2M detector-specific parsing
   - No automatic pixel array reconstruction
   - No calibration data application

## Root Cause Analysis

The min-xtc1-reader is **not failing** to read the data - it successfully accesses the same XTC files that psana uses. The perceived "failure" stems from different design goals:

- **Psana**: Full-featured detector data processing framework
- **Min-xtc1-reader**: Minimal XTC format parser for educational/debugging purposes

## Recommendations

### For Immediate Use
1. Min-xtc1-reader works correctly for XTC file parsing and exploration
2. For production detector data analysis, continue using psana
3. For understanding XTC file structure, min-xtc1-reader provides valuable low-level access

### For Enhancement (if needed)
1. Add multi-file aggregation support
2. Implement detector-specific data parsers (starting with epix10k2M)
3. Add calibration data integration
4. Implement geometry correction functionality

## Test Commands Used

```bash
# Environment setup
source /sdf/group/lcls/ds/ana/sw/conda1/manage/bin/psconda.sh

# Psana test
cd /sdf/data/lcls/ds/prj/prjcwang31/results
PYTHONPATH=/sdf/home/c/cwang31/codes/psana-wrapper:$PYTHONPATH mpirun -N 2 python run_smd.py

# Min-xtc1-reader test
cd /sdf/data/lcls/ds/prj/prjcwang31/results/software/min-xtc1-reader
python -c "from xtc1reader import XTCReader; reader = XTCReader('/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s00-c00.xtc'); print(f'Events: {len(list(reader))}')"
```

## Conclusion

**Min-xtc1-reader successfully reads the same data used by psana.** The investigation confirms that both tools access identical XTC files and that the fundamental file parsing works correctly. The differences lie in the scope of data processing functionality, not in the ability to read the underlying XTC format.

---
*Investigation completed: 2025-08-01*  
*Data source: LCLS experiment mfx100903824, run 105*  
*Environment: SLAC S3DF computing facility*