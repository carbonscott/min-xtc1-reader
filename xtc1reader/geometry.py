"""
Minimal geometry system for LCLS detectors.

Provides essential coordinate mapping and image assembly without the complexity
of the full hierarchical geometry system. Focuses on practical coordinate
transformations for common analysis tasks.
"""

import numpy as np
import os
from typing import Dict, List, Tuple, Optional, NamedTuple, TYPE_CHECKING
from dataclasses import dataclass
import math

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class DetectorSegment:
    """
    Minimal representation of a detector segment.
    
    A segment is the basic unit of a detector (e.g., CSPad 2x1, camera chip).
    """
    index: int                    # Segment index (0, 1, 2, ...)
    shape: Tuple[int, int]       # (rows, cols) in pixels
    pixel_size_um: float         # Pixel size in micrometers
    position_um: Tuple[float, float, float]  # (x, y, z) position in microns
    rotation_deg: float          # Rotation angle in degrees (0, 90, 180, 270)
    tilt_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # Fine tilt adjustments


@dataclass 
class DetectorGeometry:
    """
    Complete detector geometry with multiple segments.
    """
    name: str                    # Detector name (e.g., "cspad", "pnccd")
    segments: List[DetectorSegment]
    
    @property
    def num_segments(self) -> int:
        return len(self.segments)
    
    def get_segment(self, index: int) -> DetectorSegment:
        """Get segment by index"""
        return self.segments[index]


class CoordinateArrays(NamedTuple):
    """Pre-computed coordinate arrays for fast image assembly"""
    x_coords: 'NDArray'    # X coordinates for each pixel
    y_coords: 'NDArray'    # Y coordinates for each pixel  
    z_coords: 'NDArray'    # Z coordinates for each pixel
    pixel_areas: Optional['NDArray'] = None  # Pixel areas for intensity correction


def create_cspad_geometry() -> DetectorGeometry:
    """
    Create standard CSPad detector geometry.
    
    CSPad has 32 segments (4 quads × 8 2x1 sections each).
    Each 2x1 section is 185×388 pixels with 109.92 μm pixel size.
    """
    segments = []
    pixel_size = 109.92  # micrometers
    
    # Standard CSPad 2x1 segment shape
    segment_shape = (185, 388)
    
    # Create 32 segments with approximate positions
    # This is simplified - real CSPad has complex quad layout
    for i in range(32):
        quad = i // 8  # 0, 1, 2, 3
        section = i % 8  # 0-7 within quad
        
        # Simplified positioning - place quads in 2x2 grid
        quad_x_offset = (quad % 2) * 200000  # 200mm spacing
        quad_y_offset = (quad // 2) * 200000
        
        # Place sections within quad
        section_x_offset = (section % 4) * 42000  # ~42mm per section
        section_y_offset = (section // 4) * 20000  # ~20mm per row
        
        x_pos = quad_x_offset + section_x_offset
        y_pos = quad_y_offset + section_y_offset
        z_pos = 100000  # 100mm from interaction point
        
        # Rotation varies by quad position
        rotation = quad * 90.0  # Each quad rotated 90 degrees
        
        segment = DetectorSegment(
            index=i,
            shape=segment_shape,
            pixel_size_um=pixel_size,
            position_um=(x_pos, y_pos, z_pos),
            rotation_deg=rotation
        )
        segments.append(segment)
    
    return DetectorGeometry("cspad", segments)


def create_pnccd_geometry() -> DetectorGeometry:
    """
    Create pnCCD detector geometry.
    
    pnCCD is a single 512×512 pixel sensor with 75 μm pixels.
    """
    segment = DetectorSegment(
        index=0,
        shape=(512, 512),
        pixel_size_um=75.0,
        position_um=(0.0, 0.0, 100000.0),  # Centered, 100mm from IP
        rotation_deg=0.0
    )
    
    return DetectorGeometry("pnccd", [segment])


def create_camera_geometry(width: int, height: int, pixel_size_um: float = 24.0) -> DetectorGeometry:
    """
    Create generic camera detector geometry.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels  
        pixel_size_um: Pixel size in micrometers
    """
    segment = DetectorSegment(
        index=0,
        shape=(height, width),
        pixel_size_um=pixel_size_um,
        position_um=(0.0, 0.0, 1000000.0),  # 1m from IP
        rotation_deg=0.0
    )
    
    return DetectorGeometry("camera", [segment])


def apply_rotation_2d(x: 'NDArray', y: 'NDArray', angle_deg: float) -> Tuple['NDArray', 'NDArray']:
    """
    Apply 2D rotation to coordinate arrays.
    
    Args:
        x, y: Input coordinate arrays
        angle_deg: Rotation angle in degrees
        
    Returns:
        (x_rot, y_rot): Rotated coordinates
    """
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a
    
    return x_rot, y_rot


def compute_segment_coordinates(segment: DetectorSegment) -> Tuple['NDArray', 'NDArray', 'NDArray']:
    """
    Compute pixel coordinates for a single detector segment.
    
    Args:
        segment: DetectorSegment object
        
    Returns:
        (x_coords, y_coords, z_coords): Coordinate arrays in micrometers
    """
    rows, cols = segment.shape
    
    # Create local coordinate grids (relative to segment center)
    col_indices = np.arange(cols)
    row_indices = np.arange(rows)
    
    # Convert to physical coordinates (micrometers)
    # Center the coordinates on the segment (middle pixel at origin)
    x_local = (col_indices - (cols-1)/2) * segment.pixel_size_um
    y_local = (row_indices - (rows-1)/2) * segment.pixel_size_um
    
    # Create 2D coordinate arrays
    x_grid, y_grid = np.meshgrid(x_local, y_local)
    
    # Apply rotation
    if segment.rotation_deg != 0:
        x_rot, y_rot = apply_rotation_2d(x_grid, y_grid, segment.rotation_deg)
    else:
        x_rot, y_rot = x_grid, y_grid
    
    # Apply position offset
    x_global = x_rot + segment.position_um[0]
    y_global = y_rot + segment.position_um[1]
    z_global = np.full_like(x_global, segment.position_um[2])
    
    return x_global, y_global, z_global


def compute_detector_coordinates(geometry: DetectorGeometry) -> CoordinateArrays:
    """
    Compute coordinate arrays for entire detector.
    
    Args:
        geometry: DetectorGeometry object
        
    Returns:
        CoordinateArrays with x, y, z coordinates for all pixels
    """
    coord_arrays = []
    
    for segment in geometry.segments:
        x_seg, y_seg, z_seg = compute_segment_coordinates(segment)
        coord_arrays.append((x_seg, y_seg, z_seg))
    
    if len(coord_arrays) == 1:
        # Single segment detector
        x_coords, y_coords, z_coords = coord_arrays[0]
    else:
        # Multi-segment detector - stack along new axis
        x_list, y_list, z_list = zip(*coord_arrays)
        x_coords = np.stack(x_list, axis=0)
        y_coords = np.stack(y_list, axis=0) 
        z_coords = np.stack(z_list, axis=0)
    
    return CoordinateArrays(x_coords, y_coords, z_coords)


def parse_geometry_file(filename: str) -> DetectorGeometry:
    """
    Parse LCLS geometry file format.
    
    Args:
        filename: Path to geometry .data file
        
    Returns:
        DetectorGeometry object
    """
    segments = []
    detector_name = "unknown"
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if line.startswith('#') or not line:
                continue
            
            # Parse geometry line
            parts = line.split()
            if len(parts) < 13:
                continue
                
            try:
                # Parse fields according to format
                parent = parts[0]
                parent_ind = int(parts[1])
                object_type = parts[2]
                object_ind = int(parts[3])
                x0 = float(parts[4])
                y0 = float(parts[5]) 
                z0 = float(parts[6])
                rot_z = float(parts[7])
                rot_y = float(parts[8])
                rot_x = float(parts[9])
                tilt_z = float(parts[10])
                tilt_y = float(parts[11])
                tilt_x = float(parts[12])
                
                # Determine detector type and segment shape
                if "CSPAD" in parent:
                    detector_name = "cspad"
                    segment_shape = (185, 388)
                    pixel_size = 109.92
                elif "PNCCD" in parent:
                    detector_name = "pnccd"
                    segment_shape = (512, 512)
                    pixel_size = 75.0
                else:
                    # Default to generic detector
                    segment_shape = (100, 100)
                    pixel_size = 100.0
                
                segment = DetectorSegment(
                    index=object_ind,
                    shape=segment_shape,
                    pixel_size_um=pixel_size,
                    position_um=(x0, y0, z0),
                    rotation_deg=rot_z,  # Use Z rotation (most common)
                    tilt_deg=(tilt_x, tilt_y, tilt_z)
                )
                segments.append(segment)
                
            except (ValueError, IndexError):
                # Skip malformed lines
                continue
    
    # Sort segments by index
    segments.sort(key=lambda s: s.index)
    
    return DetectorGeometry(detector_name, segments)


def assemble_image(detector_data: 'NDArray', geometry: DetectorGeometry, 
                  method: str = "interpolate") -> 'NDArray':
    """
    Assemble detector segments into a single image.
    
    Args:
        detector_data: Raw detector data array
        geometry: DetectorGeometry object
        method: Assembly method ("interpolate" or "nearest")
        
    Returns:
        Assembled 2D image array
    """
    # Compute coordinate arrays
    coords = compute_detector_coordinates(geometry)
    
    # Find image bounds
    x_min = np.min(coords.x_coords)
    x_max = np.max(coords.x_coords)
    y_min = np.min(coords.y_coords)
    y_max = np.max(coords.y_coords)
    
    # Determine output image size (use minimum pixel size for resolution)
    min_pixel_size = min(seg.pixel_size_um for seg in geometry.segments)
    
    width = int((x_max - x_min) / min_pixel_size) + 1
    height = int((y_max - y_min) / min_pixel_size) + 1
    
    # Create output image
    image = np.zeros((height, width), dtype=np.float32)
    counts = np.zeros((height, width), dtype=np.int32)
    
    # Map detector pixels to image pixels
    for i, segment in enumerate(geometry.segments):
        if detector_data.ndim == 3:
            seg_data = detector_data[i]
        else:
            seg_data = detector_data
            
        seg_x = coords.x_coords[i] if coords.x_coords.ndim == 3 else coords.x_coords
        seg_y = coords.y_coords[i] if coords.y_coords.ndim == 3 else coords.y_coords
        
        # Convert to image coordinates
        img_x = ((seg_x - x_min) / min_pixel_size).astype(int)
        img_y = ((seg_y - y_min) / min_pixel_size).astype(int)
        
        # Clip to image bounds
        valid = (img_x >= 0) & (img_x < width) & (img_y >= 0) & (img_y < height)
        
        img_x_valid = img_x[valid]
        img_y_valid = img_y[valid]
        seg_data_valid = seg_data[valid]
        
        # Add to output image
        image[img_y_valid, img_x_valid] += seg_data_valid
        counts[img_y_valid, img_x_valid] += 1
    
    # Average overlapping pixels
    with np.errstate(divide='ignore', invalid='ignore'):
        image = np.divide(image, counts, out=np.zeros_like(image), where=counts!=0)
    
    return image


# Predefined detector geometries
DETECTOR_GEOMETRIES = {
    "cspad": create_cspad_geometry,
    "pnccd": create_pnccd_geometry,
}


def get_detector_geometry(detector_name: str, **kwargs) -> DetectorGeometry:
    """
    Get predefined detector geometry.
    
    Args:
        detector_name: Name of detector ("cspad", "pnccd", "camera")
        **kwargs: Additional arguments for geometry creation
        
    Returns:
        DetectorGeometry object
    """
    if detector_name in DETECTOR_GEOMETRIES:
        return DETECTOR_GEOMETRIES[detector_name]()
    elif detector_name == "camera":
        return create_camera_geometry(**kwargs)
    else:
        raise ValueError(f"Unknown detector: {detector_name}")


def save_coordinate_arrays(coords: CoordinateArrays, output_dir: str, prefix: str = "coords"):
    """
    Save coordinate arrays to numpy files for fast loading.
    
    Args:
        coords: CoordinateArrays object
        output_dir: Output directory
        prefix: Filename prefix
    """
    os.makedirs(output_dir, exist_ok=True)
    
    np.save(os.path.join(output_dir, f"{prefix}_x.npy"), coords.x_coords)
    np.save(os.path.join(output_dir, f"{prefix}_y.npy"), coords.y_coords)
    np.save(os.path.join(output_dir, f"{prefix}_z.npy"), coords.z_coords)
    
    if coords.pixel_areas is not None:
        np.save(os.path.join(output_dir, f"{prefix}_areas.npy"), coords.pixel_areas)


def load_coordinate_arrays(input_dir: str, prefix: str = "coords") -> CoordinateArrays:
    """
    Load coordinate arrays from numpy files.
    
    Args:
        input_dir: Input directory
        prefix: Filename prefix
        
    Returns:
        CoordinateArrays object
    """
    x_coords = np.load(os.path.join(input_dir, f"{prefix}_x.npy"))
    y_coords = np.load(os.path.join(input_dir, f"{prefix}_y.npy"))
    z_coords = np.load(os.path.join(input_dir, f"{prefix}_z.npy"))
    
    areas_file = os.path.join(input_dir, f"{prefix}_areas.npy")
    pixel_areas = np.load(areas_file) if os.path.exists(areas_file) else None
    
    return CoordinateArrays(x_coords, y_coords, z_coords, pixel_areas)