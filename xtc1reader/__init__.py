"""
Minimal XTC1 Reader Package

A lightweight Python library for reading LCLS1 XTC files without the 
full psana framework. Provides essential functionality for:
- XTC file parsing and iteration
- Basic detector geometry and coordinate mapping  
- Essential calibration (pedestals, common mode correction)

Author: Generated with Claude Code
License: MIT
"""

__version__ = "0.1.0"
__author__ = "LCLS Data Analysis"

from .xtc_reader import (
    XTCReader, Datagram, XTCContainer, XTCIterator,
    get_xtc_info, walk_xtc_tree, print_xtc_tree
)
from .binary_format import (
    parse_datagram_header, parse_xtc_header,
    TypeId, TransitionId, DamageFlags
)
from .geometry import (
    DetectorSegment, DetectorGeometry, CoordinateArrays,
    create_cspad_geometry, create_pnccd_geometry, create_camera_geometry,
    compute_segment_coordinates, compute_detector_coordinates
)
from .calibration import (
    CalibrationConstants, DetectorCalibrator, CalibrationManager,
    CommonModeCorrection, create_default_calibration, calibrate_detector_data
)
from .data_types import (
    Epix10ka2MData, parse_epix10ka2m_array, parse_detector_data
)
from .epix_utils import (
    assemble_epix10ka2m_image, get_detector_info, extract_panel, extract_quad,
    assemble_epix10ka2m_psana_compatible, get_psana_geometry_info, 
    compare_assembly_methods, validate_psana_assembly
)
from .geometry_parser import (
    parse_geometry_file, load_default_epix10ka2m_geometry, validate_geometry,
    print_geometry_summary, GeometryParseError
)
from .geometry_definitions import (
    DetectorGeometry, PanelGeometry, CoordinateArrays, PixelIndices,
    EPIX10KA2M_PANEL_SHAPE, EPIX10KA2M_NUM_PANELS, EPIX10KA2M_PIXEL_SIZE_UM
)

__all__ = [
    'XTCReader',
    'Datagram', 
    'XTCContainer',
    'XTCIterator',
    'get_xtc_info',
    'walk_xtc_tree', 
    'print_xtc_tree',
    'parse_datagram_header',
    'parse_xtc_header',
    'TypeId',
    'TransitionId', 
    'DamageFlags',
    'DetectorSegment',
    'DetectorGeometry', 
    'CoordinateArrays',
    'create_cspad_geometry',
    'create_pnccd_geometry',
    'create_camera_geometry',
    'compute_segment_coordinates',
    'compute_detector_coordinates',
    'CalibrationConstants',
    'DetectorCalibrator',
    'CalibrationManager',
    'CommonModeCorrection',
    'create_default_calibration',
    'calibrate_detector_data',
    'Epix10ka2MData',
    'parse_epix10ka2m_array',
    'parse_detector_data',
    'assemble_epix10ka2m_image',
    'get_detector_info',
    'extract_panel',
    'extract_quad',
    'assemble_epix10ka2m_psana_compatible',
    'get_psana_geometry_info',
    'compare_assembly_methods',
    'validate_psana_assembly',
    'parse_geometry_file',
    'load_default_epix10ka2m_geometry',
    'validate_geometry',
    'print_geometry_summary',
    'GeometryParseError',
    'DetectorGeometry',
    'PanelGeometry',
    'CoordinateArrays',
    'PixelIndices',
    'EPIX10KA2M_PANEL_SHAPE',
    'EPIX10KA2M_NUM_PANELS',
    'EPIX10KA2M_PIXEL_SIZE_UM'
]