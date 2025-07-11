# Minimal XTC1-Reader Package Analysis

## Executive Summary

Creating a minimal xtc1-reader Python package from the LCLS1 legacy repository would involve **moderate effort** (~2-4 weeks for an experienced developer). The package would extract only the core XTC reading, geometry handling, and calibration functionality while excluding GUI, MPI, and other complex features.

## Repository Overview

This LCLS1 repository is a comprehensive legacy codebase containing:
- **40+ packages** with extensive functionality
- **XTC file format reading** infrastructure
- **Detector geometry** handling systems
- **Calibration algorithms** and data management
- **Analysis frameworks** (psana, pyana)
- **GUI applications** and visualization tools
- **MPI support** for parallel processing

## Core Components for Minimal Reader

### 1. XTC File Reading (35% of effort)

#### Key Source Files:
- `extpkgs/pdsdata/xtc/Xtc.hh` - Core XTC container class
- `extpkgs/pdsdata/xtc/XtcFileIterator.hh/.cc` - File-based XTC reading
- `extpkgs/pdsdata/xtc/XtcIterator.hh/.cc` - Recursive XTC iteration
- `extpkgs/pdsdata/app/xtcreader.cc` - Complete example reader
- `XtcInput/XtcIterator.h/.cpp` - Enhanced iterator with damage handling
- `XtcInput/XtcStreamMerger.h/.cpp` - Multi-stream timestamp merging
- `PSXtcInput/XtcInputModule.h/.cpp` - Psana framework integration

#### Core Classes:
```cpp
class Pds::XtcFileIterator  // Low-level file iteration
class Pds::XtcIterator      // Recursive XTC traversal
class XtcInput::XtcIterator // Enhanced iterator with damage handling
class XtcInput::XtcStreamMerger // Multi-stream merging
```

#### Python Integration:
- Convert C++ classes to Python or create bindings
- Handle XTC format parsing and datagram iteration
- Support both sequential and random access patterns

### 2. Geometry Handling (30% of effort)

#### Key Source Files:
- `PSCalib/src/GeometryAccess.py` - Main geometry interface
- `PSCalib/src/GeometryObject.py` - Hierarchical geometry handling
- `PSCalib/src/SegGeometry*.py` - Detector-specific pixel layouts
- `CSPadPixCoords/include/PixCoordsCSPad.h` - CSPad coordinate handling
- `Detector/data/geometry-def-*.data` - Geometry definition files

#### Core Classes:
```python
class GeometryAccess    # Main interface for detector geometry
class GeometryObject    # Elementary geometry building block
class SegGeometry*      # Detector-specific implementations
```

#### Key Features:
- Hierarchical geometry descriptions (IP → CSPAD → SENS2X1)
- Coordinate transformations between frames (psana, lab, local)
- Pixel coordinate arrays and image assembly
- Support for multiple detector types (CSPad, EPIX, Jungfrau, PNCCD)

#### Geometry File Format:
```
# HDR PARENT IND OBJECT IND X0[um] Y0[um] Z0[um] ROT-Z ROT-Y ROT-X TILT-Z TILT-Y TILT-X
CSPAD:V2 0 SENS2X1:V1 0 51621 112683 153 90.0 0.0 0.0 0.48292 0.00000 0.00263
```

### 3. Calibration System (25% of effort)

#### Key Source Files:
- `PSCalib/src/CalibFileFinder.py` - Locate calibration files
- `PSCalib/src/NDArrIO.py` - Text file I/O for calibration arrays
- `PSCalib/src/CalibPars*.py` - Detector-specific calibration parameters
- `Detector/src/UtilsCommonMode.py` - Common mode correction algorithms
- `Detector/src/AreaDetector.py` - High-level detector interface

#### Calibration Types:
```cpp
enum CALIB_TYPE { 
    PEDESTALS=0,     // Pedestal constants
    PIXEL_STATUS,    // Bad pixel masks  
    PIXEL_RMS,       // Noise levels
    PIXEL_GAIN,      // Gain constants
    PIXEL_MASK,      // User masks
    PIXEL_BKGD,      // Background subtraction
    COMMON_MODE      // Common mode parameters
};
```

#### Common Mode Algorithms:
- **Algorithm 1:** CSPad/CSPad2x2 segment-based correction
- **Algorithm 2:** Mean-based correction for any detector
- **Algorithm 3:** Median-based correction for any detector
- **Algorithm 4:** Detector-specific median (Epix100A, FCCD960)
- **Algorithm 5:** Unbonded pixel correction

#### Calibration File Format (.data):
```
# TITLE      File to load ndarray of calibration parameters
# EXPERIMENT amo12345
# DETECTOR   Camp.0:pnCCD.1
# CALIB_TYPE pedestals
# DATE_TIME  2014-05-06 15:24:10
# DTYPE      float
# NDIM       3
# DIM:1      3
# DIM:2      4  
# DIM:3      8
```

### 4. Package Infrastructure (10% of effort)

#### Dependencies:
- **NumPy** - Essential for array operations
- **Optional:** H5py for some file formats
- **Optional:** Matplotlib for basic plotting
- Standard library: os, sys, re, struct

#### Package Structure:
```
minimal-xtc1-reader/
├── xtc1reader/
│   ├── __init__.py
│   ├── xtc/           # XTC file reading
│   ├── geometry/      # Detector geometry  
│   ├── calibration/   # Calibration system
│   └── detectors/     # Detector-specific code
├── tests/
├── examples/
├── setup.py
└── README.md
```

## Dependencies Analysis

### Current LCLS1 Dependencies:
- **Heavy:** SCons build system, extensive C++ libraries
- **Complex:** Psana framework, boost libraries
- **Platform-specific:** LCLS computing environment

### Minimal Reader Dependencies:
- **NumPy** (essential)
- **Python 3.7+** (standard library features)
- **Optional:** h5py, matplotlib for extended functionality

## Implementation Strategy

### Phase 1: Core XTC Reading (Week 1)
1. Extract and translate C++ XTC reading classes
2. Create Python XTC file iterator
3. Handle basic datagram parsing and iteration
4. Test with sample XTC files

### Phase 2: Geometry System (Week 1-2)
1. Extract GeometryAccess and GeometryObject classes
2. Implement geometry file parser for .data format
3. Add coordinate transformation algorithms
4. Support basic detector types (CSPad, area detectors)

### Phase 3: Basic Calibration (Week 2-3)
1. Extract calibration file finder and reader
2. Implement pedestal subtraction
3. Add basic common mode correction
4. Support calibration constant lookup by run number

### Phase 4: Integration and Testing (Week 3-4)
1. Create unified detector interface
2. Build comprehensive test suite
3. Add documentation and examples
4. Package for distribution

## Complexity Assessment

### Advantages:
- **Well-modularized code:** Clear separation between components
- **Text-based formats:** Calibration and geometry files are human-readable
- **Python-heavy:** Much of the high-level code is already in Python
- **Mature algorithms:** Well-tested calibration and geometry code

### Challenges:
- **C++ XTC core:** Low-level XTC reading is in C++, needs translation/bindings
- **Large codebase:** Finding all dependencies requires careful analysis
- **Detector complexity:** Multiple detector types with specific quirks
- **Testing requirements:** Need real XTC files and calibration data

## Effort Estimate: 2-4 Weeks

### Breakdown:
- **Experienced developer:** 2-3 weeks
- **Python/C++ integration:** +1 week if complex bindings needed
- **Testing and documentation:** +0.5-1 week
- **Detector-specific features:** +0.5-1 week per additional detector type

### Risk Factors:
- **Medium:** C++ to Python translation complexity
- **Low:** Dependency extraction (well-isolated modules)
- **Low:** File format complexity (well-documented)
- **Medium:** Testing without full LCLS environment

## Recommended Approach

1. **Start with pure Python components** (geometry, calibration)
2. **Create minimal XTC reader** using ctypes or pybind11 for C++ parts
3. **Focus on CSPad detector** as primary use case
4. **Build iteratively** with frequent testing
5. **Document thoroughly** for future maintenance

## Conclusion

Creating a minimal xtc1-reader package is **feasible and worthwhile**. The LCLS1 codebase contains well-designed, modular components that can be extracted and simplified. The main effort will be in carefully identifying dependencies and creating a clean Python interface to the XTC reading functionality.

The resulting package would provide:
- **XTC file reading** without full psana framework
- **Basic geometry handling** for detector coordinate mapping  
- **Essential calibration** for data processing
- **Minimal dependencies** for easy installation and maintenance

This would significantly reduce the complexity barrier for users who only need basic XTC data access functionality.