"""
Geometry definitions and data structures for detector assembly.

Based on psana geometry definition format and coordinate systems.
"""

import numpy as np
from typing import NamedTuple, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class GeometryObject:
    """
    Represents a single geometry object (panel, quad, etc.) with position and orientation.
    
    Based on psana GeometryObject format from geometry definition files.
    """
    parent: str          # Parent object name (e.g., 'CAMERA')
    parent_index: int    # Parent object index
    object_name: str     # Object name (e.g., 'EPIX10KA:V1')
    object_index: int    # Object index (0-15 for panels)
    
    # Position in micrometers
    x0: float            # X coordinate [μm]
    y0: float            # Y coordinate [μm] 
    z0: float            # Z coordinate [μm]
    
    # Rotation angles in degrees
    rot_z: float         # Rotation around Z axis [deg]
    rot_y: float         # Rotation around Y axis [deg]
    rot_x: float         # Rotation around X axis [deg]
    
    # Tilt corrections in degrees
    tilt_z: float        # Tilt around Z axis [deg]
    tilt_y: float        # Tilt around Y axis [deg]
    tilt_x: float        # Tilt around X axis [deg]


@dataclass
class PanelGeometry:
    """
    Complete geometry information for a detector panel.
    """
    panel_id: int
    shape: tuple[int, int]      # (rows, cols) - typically (352, 384)
    pixel_size_um: float        # Regular pixel size in μm
    wide_pixel_size_um: float   # Wide pixel size in μm (at ASIC boundaries)
    
    # Geometric transformation parameters
    position_um: tuple[float, float, float]    # (x0, y0, z0) in μm
    rotation_deg: tuple[float, float, float]   # (rot_z, rot_y, rot_x) in degrees
    tilt_deg: tuple[float, float, float]       # (tilt_z, tilt_y, tilt_x) in degrees
    
    def __post_init__(self):
        """Validate panel geometry parameters."""
        if self.panel_id < 0 or self.panel_id > 15:
            raise ValueError(f"Panel ID must be 0-15, got {self.panel_id}")
        
        if len(self.shape) != 2:
            raise ValueError(f"Shape must be (rows, cols), got {self.shape}")


@dataclass 
class DetectorGeometry:
    """
    Complete detector geometry with all panels and metadata.
    """
    detector_name: str
    panels: Dict[int, PanelGeometry]
    comments: Dict[str, str]
    pixel_scale_size_um: float = 100.0  # Default pixel scale for coordinate conversion
    
    def __post_init__(self):
        """Validate detector geometry."""
        if not self.panels:
            raise ValueError("Detector must have at least one panel")
        
        # Validate panel IDs are sequential
        panel_ids = sorted(self.panels.keys())
        expected_ids = list(range(len(panel_ids)))
        if panel_ids != expected_ids:
            raise ValueError(f"Panel IDs must be sequential 0-N, got {panel_ids}")
    
    @property
    def num_panels(self) -> int:
        """Number of panels in detector."""
        return len(self.panels)
    
    @property
    def total_pixels(self) -> int:
        """Total number of pixels across all panels."""
        return sum(panel.shape[0] * panel.shape[1] for panel in self.panels.values())
    
    def get_panel(self, panel_id: int) -> PanelGeometry:
        """Get geometry for specific panel."""
        if panel_id not in self.panels:
            raise ValueError(f"Panel {panel_id} not found in detector geometry")
        return self.panels[panel_id]
    
    def get_coordinate_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Get approximate coordinate bounds for all panels.
        
        Returns:
            ((xmin, xmax), (ymin, ymax)) in micrometers
        """
        # Estimate bounds based on panel positions and sizes
        # This is approximate - exact bounds require coordinate transformation
        positions = [panel.position_um for panel in self.panels.values()]
        
        if not positions:
            return ((0.0, 0.0), (0.0, 0.0))
        
        # Rough estimation: position ± panel size
        panel_size_um = 352 * 100  # Assume 100μm pixels for rough estimate
        
        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]
        
        xmin = min(x_coords) - panel_size_um
        xmax = max(x_coords) + panel_size_um
        ymin = min(y_coords) - panel_size_um
        ymax = max(y_coords) + panel_size_um
        
        return ((xmin, xmax), (ymin, ymax))


class CoordinateArrays(NamedTuple):
    """
    Pixel coordinate arrays for detector panels.
    """
    x_coords: 'NDArray'   # X coordinates in micrometers
    y_coords: 'NDArray'   # Y coordinates in micrometers
    z_coords: 'NDArray'   # Z coordinates in micrometers
    
    @property
    def shape(self) -> tuple:
        """Shape of coordinate arrays."""
        return self.x_coords.shape
    
    def bounds(self) -> dict:
        """Get coordinate bounds."""
        return {
            'x_min': float(np.min(self.x_coords)),
            'x_max': float(np.max(self.x_coords)),
            'y_min': float(np.min(self.y_coords)), 
            'y_max': float(np.max(self.y_coords)),
            'z_min': float(np.min(self.z_coords)),
            'z_max': float(np.max(self.z_coords)),
        }


class PixelIndices(NamedTuple):
    """
    Pixel indices for image assembly.
    """
    rows: 'NDArray'       # Row indices in assembled image
    cols: 'NDArray'       # Column indices in assembled image
    
    @property  
    def shape(self) -> tuple:
        """Shape of index arrays."""
        return self.rows.shape
    
    def image_shape(self) -> tuple[int, int]:
        """Calculate required image shape from indices."""
        max_row = int(np.max(self.rows)) if self.rows.size > 0 else 0
        max_col = int(np.max(self.cols)) if self.cols.size > 0 else 0
        return (max_row + 1, max_col + 1)


# Standard Epix10ka2M detector specifications
EPIX10KA2M_PANEL_SHAPE = (352, 384)
EPIX10KA2M_NUM_PANELS = 16  
EPIX10KA2M_PIXEL_SIZE_UM = 100.0
EPIX10KA2M_WIDE_PIXEL_SIZE_UM = 250.0

# Default geometry file path in lcls1 
DEFAULT_EPIX10KA2M_GEOMETRY_FILE = "/sdf/data/lcls/ds/prj/prjcwang31/results/software/lcls1/Detector/data/geometry-def-epix10ka2m.data"