"""
Coordinate transformation functions for detector geometry.

Based on psana GeometryObject coordinate transformation logic.
Implements rotations, translations, and coordinate system conversions.
"""

import numpy as np
from typing import Tuple, TYPE_CHECKING
from .geometry_definitions import PanelGeometry, CoordinateArrays, PixelIndices

if TYPE_CHECKING:
    from numpy.typing import NDArray


def apply_rotation_z(x: 'NDArray', y: 'NDArray', angle_deg: float) -> Tuple['NDArray', 'NDArray']:
    """
    Apply rotation around Z-axis.
    
    Args:
        x, y: Coordinate arrays to rotate
        angle_deg: Rotation angle in degrees
        
    Returns:
        (x_rot, y_rot): Rotated coordinate arrays
    """
    if angle_deg == 0:
        return x, y
    
    angle_rad = np.radians(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a
    
    return x_rot, y_rot


def apply_rotation_y(x: 'NDArray', z: 'NDArray', angle_deg: float) -> Tuple['NDArray', 'NDArray']:
    """
    Apply rotation around Y-axis.
    
    Args:
        x, z: Coordinate arrays to rotate
        angle_deg: Rotation angle in degrees
        
    Returns:
        (x_rot, z_rot): Rotated coordinate arrays
    """
    if angle_deg == 0:
        return x, z
    
    angle_rad = np.radians(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    x_rot = x * cos_a + z * sin_a
    z_rot = -x * sin_a + z * cos_a
    
    return x_rot, z_rot


def apply_rotation_x(y: 'NDArray', z: 'NDArray', angle_deg: float) -> Tuple['NDArray', 'NDArray']:
    """
    Apply rotation around X-axis.
    
    Args:
        y, z: Coordinate arrays to rotate
        angle_deg: Rotation angle in degrees
        
    Returns:
        (y_rot, z_rot): Rotated coordinate arrays
    """
    if angle_deg == 0:
        return y, z
    
    angle_rad = np.radians(angle_deg)
    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    
    y_rot = y * cos_a - z * sin_a
    z_rot = y * sin_a + z * cos_a
    
    return y_rot, z_rot


def apply_3d_rotation(x: 'NDArray', y: 'NDArray', z: 'NDArray', 
                     rot_z: float, rot_y: float, rot_x: float) -> Tuple['NDArray', 'NDArray', 'NDArray']:
    """
    Apply 3D rotation sequence: Z → Y → X (same as psana).
    
    Args:
        x, y, z: Coordinate arrays
        rot_z, rot_y, rot_x: Rotation angles in degrees
        
    Returns:
        (x_rot, y_rot, z_rot): Rotated coordinate arrays
    """
    # Apply rotations in order: Z, Y, X (psana convention)
    x1, y1 = apply_rotation_z(x, y, rot_z)
    z1 = z.copy()
    
    x2, z2 = apply_rotation_y(x1, z1, rot_y)
    y2 = y1.copy()
    
    y3, z3 = apply_rotation_x(y2, z2, rot_x)
    x3 = x2.copy()
    
    return x3, y3, z3


def apply_translation(x: 'NDArray', y: 'NDArray', z: 'NDArray',
                     dx: float, dy: float, dz: float) -> Tuple['NDArray', 'NDArray', 'NDArray']:
    """
    Apply translation to coordinate arrays.
    
    Args:
        x, y, z: Coordinate arrays
        dx, dy, dz: Translation offsets in micrometers
        
    Returns:
        (x_trans, y_trans, z_trans): Translated coordinate arrays
    """
    return x + dx, y + dy, z + dz


def transform_panel_coordinates(x_panel: 'NDArray', y_panel: 'NDArray', z_panel: 'NDArray',
                               panel_geometry: PanelGeometry,
                               do_tilt: bool = True) -> CoordinateArrays:
    """
    Transform panel coordinates to detector frame using full geometric transformation.
    
    This implements the same transformation as psana's GeometryObject.transform_geo_coord_arrays().
    
    Args:
        x_panel, y_panel, z_panel: Panel coordinate arrays in panel frame
        panel_geometry: Panel geometry parameters
        do_tilt: Whether to apply tilt corrections
        
    Returns:
        CoordinateArrays with transformed coordinates in detector frame
    """
    # Start with panel coordinates
    x, y, z = x_panel.copy(), y_panel.copy(), z_panel.copy()
    
    # Get transformation parameters
    pos = panel_geometry.position_um
    rot = panel_geometry.rotation_deg
    tilt = panel_geometry.tilt_deg
    
    # Apply rotations (design + tilt if enabled)
    rot_z_total = rot[0] + (tilt[0] if do_tilt else 0)
    rot_y_total = rot[1] + (tilt[1] if do_tilt else 0)
    rot_x_total = rot[2] + (tilt[2] if do_tilt else 0)
    
    x_rot, y_rot, z_rot = apply_3d_rotation(x, y, z, rot_z_total, rot_y_total, rot_x_total)
    
    # Apply translation
    x_final, y_final, z_final = apply_translation(x_rot, y_rot, z_rot, pos[0], pos[1], pos[2])
    
    return CoordinateArrays(x_final, y_final, z_final)


def coordinates_to_pixel_indices(x: 'NDArray', y: 'NDArray', 
                                pixel_scale_size_um: float = 100.0,
                                xy_offset_pix: Tuple[float, float] = (0, 0)) -> PixelIndices:
    """
    Convert physical coordinates to pixel indices for image assembly.
    
    This implements the same logic as psana's xy_to_rc_arrays() function,
    including the critical half-pixel boundary offset.
    
    Args:
        x, y: Physical coordinate arrays in micrometers
        pixel_scale_size_um: Pixel size in micrometers for scaling
        xy_offset_pix: Additional pixel offset (x_offset, y_offset)
        
    Returns:
        PixelIndices with row and column index arrays
    """
    # Find coordinate bounds
    x_min, y_min = float(np.min(x)), float(np.min(y))
    
    # Apply psana's half-pixel boundary offset (critical for correct dimensions!)
    x_min_adjusted = x_min - pixel_scale_size_um / 2
    y_min_adjusted = y_min - pixel_scale_size_um / 2
    
    # Apply additional offset if provided
    if xy_offset_pix[0] > 0:
        x_min_adjusted -= xy_offset_pix[0] * pixel_scale_size_um
    if xy_offset_pix[1] > 0:
        y_min_adjusted -= xy_offset_pix[1] * pixel_scale_size_um
    
    # Convert to pixel indices using psana's method
    # Note: In psana PSANA frame, X maps to rows, Y maps to columns
    rows = np.array((x - x_min_adjusted) / pixel_scale_size_um, dtype=np.uint32)
    cols = np.array((y - y_min_adjusted) / pixel_scale_size_um, dtype=np.uint32)
    
    return PixelIndices(rows, cols)


def calculate_detector_bounds(panels: dict, pixel_scale_size_um: float = 100.0) -> dict:
    """
    Calculate overall detector coordinate bounds and final image dimensions.
    
    Args:
        panels: Dictionary of panel geometries with coordinate arrays
        pixel_scale_size_um: Pixel scale size for dimension calculation
        
    Returns:
        Dictionary with bounds and image dimensions
    """
    if not panels:
        return {'x_min': 0, 'x_max': 0, 'y_min': 0, 'y_max': 0, 'image_shape': (0, 0)}
    
    # Collect all coordinates from all panels
    all_x = []
    all_y = []
    
    for coords in panels.values():
        all_x.append(coords.x_coords.flatten())
        all_y.append(coords.y_coords.flatten())
    
    # Combine all coordinates
    x_all = np.concatenate(all_x)
    y_all = np.concatenate(all_y)
    
    # Calculate bounds
    x_min, x_max = float(np.min(x_all)), float(np.max(x_all))
    y_min, y_max = float(np.min(y_all)), float(np.max(y_all))
    
    # Calculate image dimensions
    x_range = x_max - x_min
    y_range = y_max - y_min
    
    image_height = int(np.ceil(x_range / pixel_scale_size_um)) + 1
    image_width = int(np.ceil(y_range / pixel_scale_size_um)) + 1
    
    return {
        'x_min': x_min,
        'x_max': x_max,
        'y_min': y_min,
        'y_max': y_max,
        'x_range': x_range,
        'y_range': y_range,
        'image_shape': (image_height, image_width)
    }


def validate_coordinate_arrays(*coord_arrays: 'NDArray') -> None:
    """
    Validate that coordinate arrays have consistent shapes and valid values.
    
    Args:
        *coord_arrays: Variable number of coordinate arrays to validate
        
    Raises:
        ValueError: If arrays are inconsistent or contain invalid values
    """
    if not coord_arrays:
        return
    
    # Check shapes are consistent
    ref_shape = coord_arrays[0].shape
    for i, arr in enumerate(coord_arrays[1:], 1):
        if arr.shape != ref_shape:
            raise ValueError(f"Coordinate array {i} has shape {arr.shape}, expected {ref_shape}")
    
    # Check for invalid values
    for i, arr in enumerate(coord_arrays):
        if not np.isfinite(arr).all():
            raise ValueError(f"Coordinate array {i} contains non-finite values")
        
        # Check for reasonable coordinate ranges (±1 meter)
        if np.abs(arr).max() > 1e6:  # 1 meter in micrometers
            raise ValueError(f"Coordinate array {i} contains unreasonably large values (max: {np.abs(arr).max():.0f} μm)")


def print_transformation_summary(panel_geometry: PanelGeometry, coords_before: CoordinateArrays, 
                                coords_after: CoordinateArrays) -> None:
    """Print summary of coordinate transformation."""
    print(f"Panel {panel_geometry.panel_id} transformation:")
    print(f"  Position: {panel_geometry.position_um}")
    print(f"  Rotation: {panel_geometry.rotation_deg}°")
    print(f"  Tilt: {panel_geometry.tilt_deg}°")
    
    bounds_before = coords_before.bounds()
    bounds_after = coords_after.bounds()
    
    print(f"  Before: X=[{bounds_before['x_min']:.0f}, {bounds_before['x_max']:.0f}] μm")
    print(f"          Y=[{bounds_before['y_min']:.0f}, {bounds_before['y_max']:.0f}] μm")
    print(f"  After:  X=[{bounds_after['x_min']:.0f}, {bounds_after['x_max']:.0f}] μm")
    print(f"          Y=[{bounds_after['y_min']:.0f}, {bounds_after['y_max']:.0f}] μm")