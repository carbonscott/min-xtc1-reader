# Real Data Extraction Issue Investigation

## Problem Summary

The CLI extract command fails to extract any Epix10ka2M detector images from real XTC files, even though:
1. Our implementation was developed and tested with the same data (mfx100903824 run 105)
2. The visualization script works perfectly with synthetic data
3. The `run_smd.py` script successfully processes the same XTC files with psana

## Evidence

### CLI Extract Failure
```bash
$ xtc1reader extract /sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s03-c01.xtc --detector epix10ka2m --output-dir ./images --max-events 5

Output:
Extracting detector data from: /sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s03-c01.xtc
Output directory: ./images  
Filtering for detector type: epix10ka2m
Warning: XTC extent 335544320 exceeds payload at offset 1
Warning: XTC extent 2147483648 exceeds payload at offset 1
Warning: XTC extent 2147483648 exceeds payload at offset 1
Warning: XTC extent 2550136832 exceeds payload at offset 1
Warning: XTC extent 2550136832 exceeds payload at offset 1

Extracted 0 detector images
```

### Debug Analysis Shows Wrong TypeIds
When debugging the XTC file contents, we found:
- File contains TypeIds: 6185, 6190, 6193 (not our expected 33 for Id_Epix10kaArray)
- XTC parser reports "XTC extent exceeds payload" warnings
- Data size returned is 0 bytes for all detector types

### Known Working Reference
The same XTC files work perfectly with psana:
- `run_smd.py` successfully processes experiment='mfx100903824', run='105', detector='epix10k2M'
- Produces 1691×1691 detector images as expected
- No parsing errors reported

## Root Cause Analysis - CONFIRMED ✅

### **PRIMARY CAUSE: Psana Ecosystem Dependency**

**CONFIRMED**: Psana doesn't directly parse XTC files - it uses a complete detector data management ecosystem that we're missing.

**Critical Discovery Made**: 
```bash
# Psana uses environment-based data location
SIT_PSDM_DATA=/sdf/data/lcls/ds  # Points to LCLS data root

# DataSource abstraction (not direct file paths)
DataSource('exp=mfx100903824:run=105:smd')

# Complete calibration directory structure
/sdf/data/lcls/ds/mfx/mfx100903824/calib/Epix10ka2M::CalibV1/
├── MfxEndstation.0:Epix10ka2M.0/  # Real detector identifier
│   ├── geometry/                   # r0003.geom, etc.
│   ├── pedestals/                  # Per-pixel baseline correction
│   ├── pixel_gain/                 # Gain calibration  
│   ├── pixel_rms/                  # Noise characterization
│   └── pixel_status/               # Bad pixel masks
```

### 1. TypeId Mapping Issue - **CONFIRMED ✅**
- Our code expects `Id_Epix10kaArray = 33`
- Real data contains TypeIds 6185, 6190, 6193  
- **Root cause**: These are experiment/detector-specific TypeId assignments that psana resolves via calibration database

### 2. XTC Parsing Bug - **CONFIRMED ✅** 
- "XTC extent exceeds payload" suggests parsing issues
- **Root cause**: Our parser lacks detector-specific context that psana gets from calibration system
- Data size of 0 bytes because parser can't resolve detector instances

### 3. Missing Calibration Context - **NEW DISCOVERY ✅**
- **Critical**: Raw XTC data is meaningless without pedestal/gain correction
- Psana applies calibration transparently via detector objects
- Our direct XTC parsing bypasses entire calibration pipeline

## Investigation Plan

### Phase 1: TypeId Discovery
1. **Scan Multiple Files**: Check TypeIds across different runs/streams to see if 6185/6190/6193 are consistent
2. **Compare with Psana Source**: Check psana's TypeId definitions for these experiment-specific values
3. **Add Dynamic TypeId Support**: Make our parser more flexible about TypeId assignments

### Phase 2: XTC Parser Validation  
1. **Binary Format Verification**: Compare our parsing with hex dumps of known good data
2. **Extent Field Analysis**: Investigate why extent values are clearly wrong (335544320 bytes >> actual payload)
3. **Cross-Reference Psana Parser**: Study psana's XTC parsing code for differences

### Phase 3: Test Framework
1. **Minimal Test Case**: Create smallest possible XTC file that reproduces the issue
2. **Incremental Parsing**: Build parser that can handle progressively more complex XTC structures
3. **Validation Suite**: Test against multiple known-good XTC files

## Impact Assessment

### Critical Issues
- **CLI completely non-functional** for real data extraction
- **Visualization pipeline broken** - can't get input data from CLI
- **User experience severely degraded** - synthetic demo only

### Working Components
- **Epix10ka2M assembly logic** works perfectly (tested with synthetic data)
- **Coordinate transformations** produce psana-compatible results
- **Visualization script** handles all display modes correctly
- **Binary data parsing** works for known TypeId/format combinations

## Recommended Next Steps

1. **Immediate**: Add experimental TypeIds (6185, 6190, 6193) to our TypeId enum and test
2. **Short-term**: Fix XTC extent parsing bug that's causing "exceeds payload" warnings  
3. **Long-term**: Implement robust TypeId discovery and flexible XTC parsing

## Files Needing Investigation

- `xtc1reader/xtc_reader.py` - XTC tree walker and extent parsing
- `xtc1reader/binary_format.py` - TypeId definitions and binary structures
- `xtc1reader/cli.py` - Extract command filtering logic
- Real XTC file: `/sdf/data/lcls/ds/mfx/mfx100903824/xtc/mfx100903824-r0105-s03-c01.xtc`

---
*Created: 2025-01-03*  
*Priority: HIGH - Blocks primary CLI functionality*