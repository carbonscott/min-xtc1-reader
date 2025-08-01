"""
Parser for psana geometry definition files.

Handles parsing of geometry-def-*.data files used in LCLS1 psana for 
detector geometry definitions.
"""

import os
import re
from typing import Dict, List, Optional, TextIO
from .geometry_definitions import (
    GeometryObject, PanelGeometry, DetectorGeometry,
    EPIX10KA2M_PANEL_SHAPE, EPIX10KA2M_PIXEL_SIZE_UM, EPIX10KA2M_WIDE_PIXEL_SIZE_UM,
    DEFAULT_EPIX10KA2M_GEOMETRY_FILE
)


class GeometryParseError(Exception):
    """Exception raised when geometry file parsing fails."""
    pass


def parse_geometry_file(file_path: str) -> DetectorGeometry:
    """
    Parse psana geometry definition file.
    
    Args:
        file_path: Path to geometry-def-*.data file
        
    Returns:
        DetectorGeometry object with parsed geometry data
        
    Raises:
        GeometryParseError: If file cannot be parsed
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Geometry file not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            return _parse_geometry_stream(f, file_path)
    except Exception as e:
        raise GeometryParseError(f"Failed to parse geometry file {file_path}: {e}") from e


def _parse_geometry_stream(f: TextIO, file_path: str) -> DetectorGeometry:
    """Parse geometry from file stream."""
    geometry_objects = []
    comments = {}
    detector_name = _extract_detector_name(file_path)
    
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Parse comments
        if line.startswith('#'):
            _parse_comment_line(line, comments)
            continue
        
        # Parse geometry object line
        try:
            geo_obj = _parse_geometry_line(line)
            if geo_obj:
                geometry_objects.append(geo_obj)
        except Exception as e:
            raise GeometryParseError(f"Error parsing line {line_num}: {line}\n{e}") from e
    
    # Convert geometry objects to panel geometries
    panels = _convert_to_panel_geometries(geometry_objects)
    
    return DetectorGeometry(
        detector_name=detector_name,
        panels=panels,
        comments=comments
    )


def _extract_detector_name(file_path: str) -> str:
    """Extract detector name from file path."""
    filename = os.path.basename(file_path)
    
    # Extract from geometry-def-<detector>.data pattern
    match = re.match(r'geometry-def-(.+)\.data', filename)
    if match:
        return match.group(1)
    
    # Default to filename without extension
    return os.path.splitext(filename)[0]


def _parse_comment_line(line: str, comments: Dict[str, str]) -> None:
    """Parse comment line and extract metadata."""
    # Remove leading # and whitespace
    content = line[1:].strip()
    
    # Parse structured comments
    if ':' in content:
        # Handle COMMENT:XX format
        if content.startswith('COMMENT:'):
            match = re.match(r'COMMENT:(\d+)\s+(.+)', content)
            if match:
                key = f"COMMENT_{match.group(1).zfill(2)}"
                comments[key] = match.group(2)
        else:
            # Handle KEY value format
            parts = content.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                comments[key] = value
    else:
        # Generic comment
        comments[f"comment_{len(comments)}"] = content


def _parse_geometry_line(line: str) -> Optional[GeometryObject]:
    """Parse a single geometry definition line."""
    # Skip comment lines and headers
    if line.startswith('#') or line.startswith('HDR'):
        return None
    
    # Split line into fields
    fields = line.split()
    
    # Expected format: PARENT PARENT_IND OBJECT OBJECT_IND X0 Y0 Z0 ROT_Z ROT_Y ROT_X TILT_Z TILT_Y TILT_X
    if len(fields) < 13:
        raise ValueError(f"Insufficient fields in geometry line (expected 13, got {len(fields)})")
    
    try:
        return GeometryObject(
            parent=fields[0],
            parent_index=int(fields[1]),
            object_name=fields[2],
            object_index=int(fields[3]),
            x0=float(fields[4]),
            y0=float(fields[5]),
            z0=float(fields[6]),
            rot_z=float(fields[7]),
            rot_y=float(fields[8]),
            rot_x=float(fields[9]),
            tilt_z=float(fields[10]),
            tilt_y=float(fields[11]),
            tilt_x=float(fields[12])
        )
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid field values in geometry line: {e}") from e


def _convert_to_panel_geometries(geometry_objects: List[GeometryObject]) -> Dict[int, PanelGeometry]:
    """Convert GeometryObject list to PanelGeometry dictionary."""
    panels = {}
    
    for geo_obj in geometry_objects:
        # Filter for panel objects (EPIX10KA:V1)
        if geo_obj.object_name == 'EPIX10KA:V1':
            panel_id = geo_obj.object_index
            
            # Create PanelGeometry
            panel = PanelGeometry(
                panel_id=panel_id,
                shape=EPIX10KA2M_PANEL_SHAPE,
                pixel_size_um=EPIX10KA2M_PIXEL_SIZE_UM,
                wide_pixel_size_um=EPIX10KA2M_WIDE_PIXEL_SIZE_UM,
                position_um=(geo_obj.x0, geo_obj.y0, geo_obj.z0),
                rotation_deg=(geo_obj.rot_z, geo_obj.rot_y, geo_obj.rot_x),
                tilt_deg=(geo_obj.tilt_z, geo_obj.tilt_y, geo_obj.tilt_x)
            )
            
            panels[panel_id] = panel
    
    return panels


def load_default_epix10ka2m_geometry() -> DetectorGeometry:
    """
    Load default Epix10ka2M geometry from standard location.
    
    Returns:
        DetectorGeometry for Epix10ka2M
        
    Raises:
        GeometryParseError: If default geometry file cannot be loaded
    """
    return parse_geometry_file(DEFAULT_EPIX10KA2M_GEOMETRY_FILE)


def validate_geometry(geometry: DetectorGeometry) -> List[str]:
    """
    Validate geometry definition and return list of issues found.
    
    Args:
        geometry: DetectorGeometry to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    issues = []
    
    # Check panel count
    if geometry.num_panels != 16:
        issues.append(f"Expected 16 panels for Epix10ka2M, got {geometry.num_panels}")
    
    # Check panel IDs
    expected_ids = set(range(16))
    actual_ids = set(geometry.panels.keys())
    missing_ids = expected_ids - actual_ids
    extra_ids = actual_ids - expected_ids
    
    if missing_ids:
        issues.append(f"Missing panel IDs: {sorted(missing_ids)}")
    if extra_ids:
        issues.append(f"Unexpected panel IDs: {sorted(extra_ids)}")
    
    # Check panel shapes
    for panel_id, panel in geometry.panels.items():
        if panel.shape != EPIX10KA2M_PANEL_SHAPE:
            issues.append(f"Panel {panel_id} has wrong shape: {panel.shape} (expected {EPIX10KA2M_PANEL_SHAPE})")
    
    # Check for reasonable coordinate ranges
    bounds = geometry.get_coordinate_bounds()
    x_range = bounds[0][1] - bounds[0][0]
    y_range = bounds[1][1] - bounds[1][0]
    
    if x_range < 50000 or x_range > 200000:  # 50-200mm seems reasonable
        issues.append(f"X coordinate range seems unreasonable: {x_range:.0f} μm")
    if y_range < 50000 or y_range > 200000:
        issues.append(f"Y coordinate range seems unreasonable: {y_range:.0f} μm")
    
    return issues


def print_geometry_summary(geometry: DetectorGeometry) -> None:
    """Print summary of detector geometry."""
    print(f"Detector: {geometry.detector_name}")
    print(f"Panels: {geometry.num_panels}")
    print(f"Total pixels: {geometry.total_pixels:,}")
    
    bounds = geometry.get_coordinate_bounds()
    print(f"Coordinate bounds:")
    print(f"  X: {bounds[0][0]:.0f} to {bounds[0][1]:.0f} μm")
    print(f"  Y: {bounds[1][0]:.0f} to {bounds[1][1]:.0f} μm")
    
    if geometry.comments:
        print(f"Comments: {len(geometry.comments)}")
        for key, value in list(geometry.comments.items())[:3]:
            print(f"  {key}: {value}")
        if len(geometry.comments) > 3:
            print(f"  ... and {len(geometry.comments) - 3} more")
    
    # Show first few panels
    print("\nPanel positions (first 4):")
    for panel_id in sorted(geometry.panels.keys())[:4]:
        panel = geometry.panels[panel_id]
        pos = panel.position_um
        rot = panel.rotation_deg
        print(f"  Panel {panel_id}: pos=({pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f}) μm, rot_z={rot[0]:.0f}°")
    
    if geometry.num_panels > 4:
        print(f"  ... and {geometry.num_panels - 4} more panels")