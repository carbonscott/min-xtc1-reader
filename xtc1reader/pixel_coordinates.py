"""
Pixel coordinate generation for detector panels.

Based on psana SegGeometryEpix10kaV1 coordinate generation logic.
Handles regular and wide pixels at ASIC boundaries.
"""

import numpy as np
from typing import TYPE_CHECKING
from .geometry_definitions import PanelGeometry, CoordinateArrays

if TYPE_CHECKING:
    from numpy.typing import NDArray


def generate_epix10ka_panel_coordinates(panel_geometry: PanelGeometry) -> CoordinateArrays:
    """
    Generate pixel coordinate arrays for a single Epix10ka panel.
    
    Based on psana's SegGeometryEpix10kaV1.pixel_coord_array() method.
    Creates 352×384 coordinate arrays with proper handling of wide pixels.
    
    Args:
        panel_geometry: Panel geometric parameters
        
    Returns:
        CoordinateArrays with X, Y, Z coordinates in panel frame
    """
    rows, cols = panel_geometry.shape  # Should be (352, 384)
    pixel_size = panel_geometry.pixel_size_um  # 100 μm
    wide_pixel_size = panel_geometry.wide_pixel_size_um  # 250 μm
    
    # Generate coordinate arrays using psana's algorithm
    x_coords, y_coords = _generate_epix10ka_xy_arrays(rows, cols, pixel_size, wide_pixel_size)
    
    # Z coordinates are all zero in panel frame (flat detector)
    z_coords = np.zeros_like(x_coords)
    
    return CoordinateArrays(x_coords, y_coords, z_coords)


def _generate_epix10ka_xy_arrays(rows: int, cols: int, pixel_size: float, 
                                wide_pixel_size: float) -> tuple['NDArray', 'NDArray']:
    """
    Generate X,Y coordinate arrays for Epix10ka panel using psana's exact algorithm.
    
    This precisely implements psana's SegGeometryEpix10kaV1.make_pixel_coord_arrs() method.
    
    Args:
        rows, cols: Panel dimensions (352, 384)
        pixel_size: Regular pixel size in μm (100)  
        wide_pixel_size: Wide pixel size in μm (250)
        
    Returns:
        (x_array, y_array): Coordinate arrays in micrometers
    """
    # Psana constants
    colsh = cols // 2  # 192
    rowsh = rows // 2  # 176  
    pixsh = pixel_size / 2  # 50
    pixwh = wide_pixel_size / 2  # 125
    
    # Generate X coordinates (psana's exact algorithm)
    # x_rhs = np.arange(colsh) * pixs + pixw - pixsh
    x_rhs = np.arange(colsh) * pixel_size + wide_pixel_size - pixsh
    # Set wide pixel center: x_rhs[0] = pixwh
    x_rhs[0] = pixwh
    # x_arr_um = np.hstack([-x_rhs[::-1], x_rhs])
    x_arr_um = np.hstack([-x_rhs[::-1], x_rhs])
    
    # Generate Y coordinates (psana's exact algorithm)  
    # y_rhs = np.arange(rowsh) * pixs + pixw - pixsh
    y_rhs = np.arange(rowsh) * pixel_size + wide_pixel_size - pixsh
    # Set wide pixel center: y_rhs[0] = pixwh  
    y_rhs[0] = pixwh
    # y_arr_um = np.hstack([y_rhs[::-1], -y_rhs]) - reverse sign
    y_arr_um = np.hstack([y_rhs[::-1], -y_rhs])
    
    # Create 2D meshgrid (psana uses standard indexing)
    x_pix_arr_um, y_pix_arr_um = np.meshgrid(x_arr_um, y_arr_um)
    
    return x_pix_arr_um, y_pix_arr_um


# Note: Using psana's exact coordinate generation algorithm above
# No separate row/column coordinate functions needed


def generate_detector_coordinates(detector_geometry, do_tilt: bool = True) -> dict:
    """
    Generate coordinate arrays for all panels in detector.
    
    Args:
        detector_geometry: DetectorGeometry object
        do_tilt: Whether to apply tilt corrections
        
    Returns:
        Dictionary mapping panel_id to transformed CoordinateArrays
    """
    from .coordinate_transform import transform_panel_coordinates
    
    panel_coordinates = {}
    
    for panel_id, panel_geom in detector_geometry.panels.items():
        # Generate panel coordinates in panel frame
        panel_coords = generate_epix10ka_panel_coordinates(panel_geom)
        
        # Transform to detector frame
        detector_coords = transform_panel_coordinates(
            panel_coords.x_coords, 
            panel_coords.y_coords, 
            panel_coords.z_coords,
            panel_geom,
            do_tilt=do_tilt
        )
        
        panel_coordinates[panel_id] = detector_coords
    
    return panel_coordinates


def validate_panel_coordinates(coords: CoordinateArrays, expected_shape: tuple) -> list:
    """
    Validate panel coordinate arrays.
    
    Args:
        coords: CoordinateArrays to validate
        expected_shape: Expected shape (rows, cols)
        
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    # Check shapes
    if coords.shape != expected_shape:
        issues.append(f"Coordinate shape {coords.shape} != expected {expected_shape}")
    
    # Check for finite values
    for name, arr in [('X', coords.x_coords), ('Y', coords.y_coords), ('Z', coords.z_coords)]:
        if not np.isfinite(arr).all():
            issues.append(f"{name} coordinates contain non-finite values")
    
    # Check coordinate ranges are reasonable for a detector panel
    x_range = coords.x_coords.max() - coords.x_coords.min()
    y_range = coords.y_coords.max() - coords.y_coords.min()
    
    # Epix10ka panel is roughly 35mm × 38mm
    if x_range < 30000 or x_range > 50000:  # 30-50mm
        issues.append(f"X coordinate range {x_range:.0f} μm seems unreasonable for panel")
    if y_range < 30000 or y_range > 50000:
        issues.append(f"Y coordinate range {y_range:.0f} μm seems unreasonable for panel")
    
    return issues


def print_coordinate_summary(panel_id: int, coords: CoordinateArrays) -> None:
    """Print summary of panel coordinates."""
    bounds = coords.bounds()
    
    print(f"Panel {panel_id} coordinates:")
    print(f"  Shape: {coords.shape}")
    print(f"  X range: {bounds['x_min']:.1f} to {bounds['x_max']:.1f} μm ({bounds['x_max'] - bounds['x_min']:.1f} μm)")
    print(f"  Y range: {bounds['y_min']:.1f} to {bounds['y_max']:.1f} μm ({bounds['y_max'] - bounds['y_min']:.1f} μm)")
    print(f"  Z range: {bounds['z_min']:.1f} to {bounds['z_max']:.1f} μm")


def get_pixel_areas(panel_geometry: PanelGeometry) -> 'NDArray':
    """
    Get pixel area array for panel (for masking or weighting).
    
    Args:
        panel_geometry: Panel geometry parameters
        
    Returns:
        Array of pixel areas (1.0 for regular pixels, 2.5 for wide pixels)
    """
    rows, cols = panel_geometry.shape
    pixel_size = panel_geometry.pixel_size_um
    wide_pixel_size = panel_geometry.wide_pixel_size_um
    
    # Start with regular pixel areas
    areas = np.ones((rows, cols), dtype=np.float32)
    
    # Mark wide pixels (at ASIC boundaries)
    asic_rows, asic_cols = 176, 192
    
    # Wide pixels in row direction (between vertically stacked ASICs)
    areas[asic_rows, :] = wide_pixel_size / pixel_size
    
    # Wide pixels in column direction (between horizontally adjacent ASICs)  
    areas[:, asic_cols] = wide_pixel_size / pixel_size
    
    # Corner pixel is wide in both directions
    areas[asic_rows, asic_cols] = (wide_pixel_size / pixel_size) ** 2
    
    return areas