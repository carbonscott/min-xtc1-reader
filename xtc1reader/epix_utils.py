"""
Epix detector utilities for image assembly and processing.

Based on psana UtilsEpix10ka2M.py functionality, specifically the
table_nxn_epix10ka_from_ndarr() function for image assembly.
"""

import numpy as np
from typing import TYPE_CHECKING, Optional
from .geometry_definitions import DetectorGeometry, CoordinateArrays, PixelIndices
from .geometry_parser import load_default_epix10ka2m_geometry
from .pixel_coordinates import generate_detector_coordinates
from .coordinate_transform import coordinates_to_pixel_indices, calculate_detector_bounds

if TYPE_CHECKING:
    from numpy.typing import NDArray


def assemble_epix10ka2m_image(frames: 'NDArray', include_gaps: bool = True) -> 'NDArray':
    """
    Convert Epix10ka2M raw panel data to assembled 2D image.
    
    The Epix10ka2M detector consists of 16 panels (352x384 each) arranged as:
    - 4 quads, each containing 4 panels in a 2x2 arrangement
    - Quads are arranged horizontally: [Quad0][Quad1][Quad2][Quad3]
    - Within each quad, panels are arranged as: [(3,2), (1,0)]
    
    Args:
        frames: Input array shaped (16, 352, 384) or compatible
        include_gaps: Whether to include gaps between panels/quads
        
    Returns:
        Assembled 2D image array
        
    Raises:
        ValueError: If input array has wrong shape
    """
    frames = np.asarray(frames)
    
    # Handle different input shapes
    if frames.ndim == 2 and frames.size == 352 * 384:
        # Single panel
        return frames.reshape(352, 384)
    
    elif frames.ndim == 3 and frames.shape[0] == 4:
        # Quad data (4 panels) - arrange as 2x2
        return _assemble_quad_image(frames, include_gaps)
    
    elif frames.ndim == 3 and frames.shape[0] == 16:
        # Full detector (16 panels) - arrange as 4 quads horizontally
        return _assemble_full_detector_image(frames, include_gaps)
    
    else:
        raise ValueError(f"Unsupported frame shape: {frames.shape}. "
                        f"Expected (352,384), (4,352,384), or (16,352,384)")


def _assemble_quad_image(quad_frames: 'NDArray', include_gaps: bool = True) -> 'NDArray':
    """
    Assemble 4 panels into a quad image.
    
    Panel arrangement: [(3,2), (1,0)] - panels are numbered and arranged as:
    ┌─────┬─────┐
    │  3  │  2  │
    ├─────┼─────┤  
    │  1  │  0  │
    └─────┴─────┘
    """
    if quad_frames.shape != (4, 352, 384):
        raise ValueError(f"Expected quad shape (4, 352, 384), got {quad_frames.shape}")
    
    if include_gaps:
        gap_h = 20  # Horizontal gap between panels
        gap_v = 20  # Vertical gap between panel rows
        
        # Create gaps
        h_gap = np.zeros((352, gap_h), dtype=quad_frames.dtype)
        v_gap = np.zeros((gap_v, 2*384 + gap_h), dtype=quad_frames.dtype)
        
        # Assemble top row: panel 3, gap, panel 2  
        top_row = np.hstack([quad_frames[3], h_gap, quad_frames[2]])
        
        # Assemble bottom row: panel 1, gap, panel 0
        bottom_row = np.hstack([quad_frames[1], h_gap, quad_frames[0]])
        
        # Stack with vertical gap
        return np.vstack([top_row, v_gap, bottom_row])
    
    else:
        # No gaps - simple arrangement
        top_row = np.hstack([quad_frames[3], quad_frames[2]])
        bottom_row = np.hstack([quad_frames[1], quad_frames[0]])
        return np.vstack([top_row, bottom_row])


def _assemble_full_detector_image(frames: 'NDArray', include_gaps: bool = True) -> 'NDArray':
    """
    Assemble all 16 panels into full detector image.
    
    Layout: 4 quads arranged horizontally
    [Quad0][Quad1][Quad2][Quad3]
    
    Each quad contains panels 0-3, 4-7, 8-11, 12-15 respectively.
    """
    if frames.shape != (16, 352, 384):
        raise ValueError(f"Expected shape (16, 352, 384), got {frames.shape}")
    
    # Split into quads (4 panels each)
    quads = frames.reshape(4, 4, 352, 384)
    
    # Assemble each quad
    quad_images = []
    for i in range(4):
        quad_img = _assemble_quad_image(quads[i], include_gaps=include_gaps)
        quad_images.append(quad_img)
    
    if include_gaps:
        # Add gaps between quads
        gap_width = 50
        quad_gap = np.zeros((quad_images[0].shape[0], gap_width), dtype=frames.dtype)
        
        # Arrange quads horizontally with gaps
        result = quad_images[0]
        for quad_img in quad_images[1:]:
            result = np.hstack([result, quad_gap, quad_img])
        
        return result
    
    else:
        # No gaps - simple horizontal arrangement
        return np.hstack(quad_images)


def get_panel_coordinates(panel_id: int, include_gaps: bool = True) -> tuple[slice, slice]:
    """
    Get the (row, col) slices for a specific panel in the assembled image.
    
    Args:
        panel_id: Panel number (0-15)
        include_gaps: Whether gaps are included in the assembled image
        
    Returns:
        (row_slice, col_slice) for accessing the panel in assembled image
    """
    if not 0 <= panel_id <= 15:
        raise ValueError(f"Panel ID must be 0-15, got {panel_id}")
    
    # Determine quad and panel within quad
    quad_id = panel_id // 4
    panel_in_quad = panel_id % 4
    
    # Panel dimensions
    panel_rows, panel_cols = 352, 384
    
    if include_gaps:
        gap_h, gap_v = 20, 20
        gap_between_quads = 50
        
        # Quad dimensions with gaps
        quad_rows = 2 * panel_rows + gap_v
        quad_cols = 2 * panel_cols + gap_h
        
        # Panel positions within quad (with gaps)
        panel_positions = {
            0: (panel_rows + gap_v, panel_cols + gap_h),  # Bottom right
            1: (panel_rows + gap_v, 0),                    # Bottom left  
            2: (0, panel_cols + gap_h),                    # Top right
            3: (0, 0)                                      # Top left
        }
        
        # Quad start position
        quad_col_start = quad_id * (quad_cols + gap_between_quads)
        panel_row_start, panel_col_start = panel_positions[panel_in_quad]
        panel_col_start += quad_col_start
        
    else:
        # No gaps
        quad_rows = 2 * panel_rows
        quad_cols = 2 * panel_cols
        
        panel_positions = {
            0: (panel_rows, panel_cols),  # Bottom right
            1: (panel_rows, 0),           # Bottom left
            2: (0, panel_cols),           # Top right  
            3: (0, 0)                     # Top left
        }
        
        quad_col_start = quad_id * quad_cols
        panel_row_start, panel_col_start = panel_positions[panel_in_quad]
        panel_col_start += quad_col_start
    
    # Create slices
    row_slice = slice(panel_row_start, panel_row_start + panel_rows)
    col_slice = slice(panel_col_start, panel_col_start + panel_cols)
    
    return row_slice, col_slice


def get_detector_info() -> dict:
    """
    Get information about the Epix10ka2M detector geometry.
    
    Returns:
        Dictionary with detector specifications
    """
    return {
        'name': 'Epix10ka2M',
        'num_panels': 16,
        'num_quads': 4,
        'panels_per_quad': 4,
        'panel_shape': (352, 384),
        'pixel_size_um': 100.0,  # 100 micron pixels
        'total_pixels': 16 * 352 * 384,
        'assembled_shape_no_gaps': (2*352, 4*2*384),  # (704, 3072)
        'assembled_shape_with_gaps': (2*352 + 20, 4*(2*384 + 20) + 3*50),  # ~(724, 3228)
    }


# Convenience functions for common operations

def extract_panel(frames: 'NDArray', panel_id: int) -> 'NDArray':
    """Extract a specific panel from the frame array."""
    if frames.shape[0] != 16:
        raise ValueError(f"Expected 16 panels, got {frames.shape[0]}")
    return frames[panel_id]


def extract_quad(frames: 'NDArray', quad_id: int) -> 'NDArray':
    """Extract a specific quad (4 panels) from the frame array."""
    if not 0 <= quad_id <= 3:
        raise ValueError(f"Quad ID must be 0-3, got {quad_id}")
    
    start_panel = quad_id * 4
    return frames[start_panel:start_panel + 4]


def calculate_detector_stats(frames: 'NDArray') -> dict:
    """Calculate basic statistics for detector data."""
    return {
        'shape': frames.shape,
        'dtype': frames.dtype,
        'min': np.min(frames),
        'max': np.max(frames),
        'mean': np.mean(frames),
        'std': np.std(frames),
        'total_pixels': frames.size,
    }


# ============================================================================
# Psana-Compatible Advanced Image Assembly Functions
# ============================================================================

def assemble_epix10ka2m_psana_compatible(frames: 'NDArray', 
                                        geometry: Optional[DetectorGeometry] = None,
                                        do_tilt: bool = True,
                                        pixel_scale_size_um: float = 100.0) -> 'NDArray':
    """
    Assemble Epix10ka2M detector image using psana-compatible coordinate-based method.
    
    This produces images matching psana's .image() output (~1691×1691 pixels).
    
    Args:
        frames: Raw detector data shaped (16, 352, 384)
        geometry: Detector geometry (loads default if None)
        do_tilt: Whether to apply tilt corrections
        pixel_scale_size_um: Pixel scale size for coordinate conversion
        
    Returns:
        Assembled detector image with psana-compatible dimensions
        
    Raises:
        ValueError: If frames have wrong shape or geometry is invalid
    """
    frames = np.asarray(frames)
    
    # Validate input
    if frames.shape != (16, 352, 384):
        raise ValueError(f"Expected frames shape (16, 352, 384), got {frames.shape}")
    
    # Load default geometry if not provided
    if geometry is None:
        try:
            geometry = load_default_epix10ka2m_geometry()
        except Exception as e:
            raise ValueError(f"Failed to load default Epix10ka2M geometry: {e}") from e
    
    # Generate coordinate arrays for all panels
    panel_coordinates = generate_detector_coordinates(geometry, do_tilt=do_tilt)
    
    # Create assembled image using psana-compatible coordinate-based pixel mapping
    assembled_image = img_from_pixel_arrays(
        panel_coordinates, frames, pixel_scale_size_um
    )
    
    return assembled_image


def img_from_pixel_arrays(panel_coordinates: dict, frames: 'NDArray', 
                         pixel_scale_size_um: float) -> 'NDArray':
    """
    Create assembled image from pixel coordinate arrays and detector data.
    
    This implements the same algorithm as psana's img_from_pixel_arrays() function.
    Uses direct pixel-to-pixel mapping without interpolation and calculates
    final image dimensions based on maximum pixel indices (psana method).
    
    Args:
        panel_coordinates: Dictionary of panel coordinate arrays
        frames: Raw detector data (16, 352, 384)
        pixel_scale_size_um: Pixel scale size for coordinate conversion
        
    Returns:
        Assembled detector image
    """
    # Collect all coordinates to determine global bounds with psana's method
    all_x = []
    all_y = []
    all_data = []
    all_row_indices = []
    all_col_indices = []
    
    for panel_id in range(16):
        if panel_id not in panel_coordinates:
            continue
            
        coords = panel_coordinates[panel_id]
        panel_data = frames[panel_id]
        
        all_x.append(coords.x_coords.flatten())
        all_y.append(coords.y_coords.flatten())
        all_data.append(panel_data.flatten())
    
    if not all_x:
        return np.zeros((1, 1), dtype=frames.dtype)
    
    # Combine all coordinates
    x_all = np.concatenate(all_x)
    y_all = np.concatenate(all_y)
    data_all = np.concatenate(all_data)
    
    # Apply psana's coordinate-to-pixel conversion with half-pixel offset
    x_min = float(np.min(x_all))
    y_min = float(np.min(y_all))
    
    # Critical: psana's half-pixel boundary offset
    x_min_adjusted = x_min - pixel_scale_size_um / 2
    y_min_adjusted = y_min - pixel_scale_size_um / 2
    
    # Convert to pixel indices using psana's exact method
    row_indices = np.array((x_all - x_min_adjusted) / pixel_scale_size_um, dtype=np.uint32)
    col_indices = np.array((y_all - y_min_adjusted) / pixel_scale_size_um, dtype=np.uint32)
    
    # Calculate image dimensions using psana's method: max(indices) + 1
    image_height = int(np.max(row_indices)) + 1
    image_width = int(np.max(col_indices)) + 1
    
    # Initialize output image
    image = np.zeros((image_height, image_width), dtype=frames.dtype)
    
    # Direct pixel assignment (last value wins for overlaps)
    image[row_indices, col_indices] = data_all
    
    return image


def get_psana_geometry_info(geometry: Optional[DetectorGeometry] = None) -> dict:
    """
    Get detailed geometry information in psana-compatible format.
    
    Args:
        geometry: Detector geometry (loads default if None)
        
    Returns:
        Dictionary with geometry information
    """
    if geometry is None:
        geometry = load_default_epix10ka2m_geometry()
    
    # Generate coordinates to get bounds
    panel_coordinates = generate_detector_coordinates(geometry, do_tilt=True)
    bounds = calculate_detector_bounds(panel_coordinates)
    
    return {
        'detector_name': geometry.detector_name,
        'num_panels': geometry.num_panels,
        'panel_shape': (352, 384),
        'total_pixels': geometry.total_pixels,
        'coordinate_bounds': {
            'x_min': bounds['x_min'],
            'x_max': bounds['x_max'],
            'y_min': bounds['y_min'],
            'y_max': bounds['y_max'],
            'x_range': bounds['x_range'],
            'y_range': bounds['y_range']
        },
        'assembled_image_shape': bounds['image_shape'],
        'pixel_scale_size_um': 100.0,
        'geometry_comments': geometry.comments
    }


def compare_assembly_methods(frames: 'NDArray') -> dict:
    """
    Compare simple vs psana-compatible assembly methods.
    
    Args:
        frames: Raw detector data (16, 352, 384)
        
    Returns:
        Dictionary with comparison results
    """
    # Simple assembly
    simple_image = assemble_epix10ka2m_image(frames, include_gaps=False)
    
    # Psana-compatible assembly  
    psana_image = assemble_epix10ka2m_psana_compatible(frames)
    
    return {
        'simple_assembly': {
            'shape': simple_image.shape,
            'method': 'Simple panel arrangement',
            'total_pixels': simple_image.size,
            'non_zero_pixels': np.count_nonzero(simple_image)
        },
        'psana_assembly': {
            'shape': psana_image.shape, 
            'method': 'Coordinate-based geometric assembly',
            'total_pixels': psana_image.size,
            'non_zero_pixels': np.count_nonzero(psana_image)
        },
        'comparison': {
            'shape_ratio': (psana_image.size / simple_image.size),
            'coverage_simple': (np.count_nonzero(simple_image) / simple_image.size) * 100,
            'coverage_psana': (np.count_nonzero(psana_image) / psana_image.size) * 100
        }
    }


def validate_psana_assembly(frames: 'NDArray', expected_shape: Optional[tuple] = None) -> dict:
    """
    Validate psana-compatible assembly results.
    
    Args:
        frames: Raw detector data
        expected_shape: Expected output shape (defaults to ~1691×1691)
        
    Returns:
        Dictionary with validation results
    """
    try:
        # Perform assembly
        assembled = assemble_epix10ka2m_psana_compatible(frames)
        
        # Get geometry info
        geom_info = get_psana_geometry_info()
        
        # Validation checks
        issues = []
        
        # Check shape is reasonable
        height, width = assembled.shape
        if expected_shape:
            if assembled.shape != expected_shape:
                issues.append(f"Shape {assembled.shape} != expected {expected_shape}")
        else:
            # Check for reasonable dimensions (should be ~1600-1800 pixels)
            if height < 1600 or height > 1800:
                issues.append(f"Height {height} outside expected range 1600-1800")
            if width < 1600 or width > 1800:
                issues.append(f"Width {width} outside expected range 1600-1800")
        
        # Check for data presence
        non_zero_pixels = np.count_nonzero(assembled)
        expected_detector_pixels = 16 * 352 * 384  # Raw detector pixels
        coverage = (non_zero_pixels / assembled.size) * 100
        
        if non_zero_pixels < expected_detector_pixels * 0.9:
            issues.append(f"Too few non-zero pixels: {non_zero_pixels} (expected ~{expected_detector_pixels})")
        
        if coverage < 60:  # Should cover reasonable fraction of assembled image
            issues.append(f"Low pixel coverage: {coverage:.1f}%")
        
        return {
            'success': len(issues) == 0,
            'issues': issues,
            'result_shape': assembled.shape,
            'non_zero_pixels': int(non_zero_pixels),
            'pixel_coverage_percent': float(coverage),
            'geometry_info': geom_info
        }
        
    except Exception as e:
        return {
            'success': False,
            'issues': [f"Assembly failed: {e}"],
            'error': str(e)
        }