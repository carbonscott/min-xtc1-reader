"""
Data type parsers for common LCLS detectors.

Handles decoding of binary data for various detector types found in XTC files.
"""

import struct
import numpy as np
from typing import NamedTuple, Optional, Any, TYPE_CHECKING
from .binary_format import TypeId

if TYPE_CHECKING:
    from numpy.typing import NDArray

class CameraFrame(NamedTuple):
    """Parsed camera frame data"""
    width: int
    height: int
    depth: int  # bits per pixel
    offset: int
    data: 'NDArray'  # 2D array of pixel values
    
    
class CSPadElement(NamedTuple):
    """Parsed CSPad element (2x1 section) data"""
    quad: int
    section: int  
    data: 'NDArray'  # Shape: (185, 388) for standard CSPad 2x1
    common_mode: Optional['NDArray'] = None


class CSPadConfig(NamedTuple):
    """CSPad configuration information"""
    quad_mask: int  # Which quads are active
    asic_mask: int  # Which ASICs are active  
    run_delay: int
    event_code: int
    # Simplified - real config has many more fields


class Epix10ka2MData(NamedTuple):
    """Parsed Epix10ka2M detector data"""
    frame_number: int
    frames: 'NDArray'  # Shape: (16, 352, 384) - 16 panels of 352x384 pixels each
    timestamp: Optional[float] = None
    
    @property
    def num_panels(self) -> int:
        """Number of detector panels"""
        return 16
    
    @property  
    def panel_shape(self) -> tuple[int, int]:
        """Shape of individual panel"""
        return (352, 384)


def parse_camera_frame(data: bytes, type_id: int, version: int) -> CameraFrame:
    """
    Parse camera frame data from XTC payload.
    
    Args:
        data: Raw frame data bytes
        type_id: Type ID from XTC header
        version: Version from XTC header
        
    Returns:
        CameraFrame with decoded image data
    """
    if len(data) < 16:
        raise ValueError("Camera frame data too short")
    
    # Parse frame header - format varies by camera type
    if type_id == TypeId.Id_Frame:
        # Generic frame format
        width, height, depth, offset = struct.unpack('<4I', data[0:16])
        
        # Calculate expected data size
        bytes_per_pixel = (depth + 7) // 8  # Round up to nearest byte
        expected_size = width * height * bytes_per_pixel
        
        if len(data) < 16 + expected_size:
            raise ValueError(f"Frame data truncated: {len(data)} < {16 + expected_size}")
        
        # Extract pixel data
        pixel_data = data[16:16 + expected_size]
        
        # Convert to numpy array based on depth
        if depth <= 8:
            dtype = np.uint8
        elif depth <= 16:
            dtype = np.uint16
        else:
            dtype = np.uint32
            
        # Parse pixel data (little-endian)
        if dtype == np.uint8:
            pixels = np.frombuffer(pixel_data, dtype=np.uint8)
        elif dtype == np.uint16:
            pixels = np.frombuffer(pixel_data, dtype='<u2')  # little-endian uint16
        else:
            pixels = np.frombuffer(pixel_data, dtype='<u4')  # little-endian uint32
        
        # Reshape to 2D image
        image = pixels.reshape((height, width))
        
        return CameraFrame(width, height, depth, offset, image)
    
    else:
        raise ValueError(f"Unsupported camera type: {type_id}")


def parse_pnccd_frame(data: bytes, version: int) -> CameraFrame:
    """
    Parse pnCCD frame data.
    
    pnCCD has fixed format: 512x512 pixels, 16-bit depth
    """
    if version == 1:
        # pnCCD frame is just raw pixel data, no header
        expected_size = 512 * 512 * 2  # 16-bit pixels
        
        if len(data) < expected_size:
            raise ValueError(f"pnCCD frame data too short: {len(data)} < {expected_size}")
        
        # Parse as little-endian uint16
        pixels = np.frombuffer(data[:expected_size], dtype='<u2')
        image = pixels.reshape((512, 512))
        
        return CameraFrame(512, 512, 16, 0, image)
    
    else:
        raise ValueError(f"Unsupported pnCCD version: {version}")


def parse_cspad_element(data: bytes, version: int) -> CSPadElement:
    """
    Parse CSPad element (2x1 section) data.
    
    CSPad elements have fixed format: 185x388 pixels, 16-bit
    """
    if version in [1, 2]:
        # CSPad element format
        if len(data) < 16:
            raise ValueError("CSPad element header too short")
        
        # Parse element header
        tid, acq_count, op_code, quad, sect_id = struct.unpack('<5I', data[0:20])
        
        # Calculate remaining data for pixels
        pixel_data_size = 185 * 388 * 2  # 16-bit pixels
        
        if len(data) < 20 + pixel_data_size:
            raise ValueError(f"CSPad element data too short: {len(data)} < {20 + pixel_data_size}")
        
        # Extract pixel data  
        pixel_data = data[20:20 + pixel_data_size]
        pixels = np.frombuffer(pixel_data, dtype='<u2')  # little-endian uint16
        image = pixels.reshape((185, 388))
        
        return CSPadElement(quad, sect_id, image)
    
    else:
        raise ValueError(f"Unsupported CSPad element version: {version}")


def parse_cspad_config(data: bytes, version: int) -> CSPadConfig:
    """
    Parse CSPad configuration data.
    
    This is simplified - real CSPad config has many more fields
    """
    if len(data) < 16:
        raise ValueError("CSPad config data too short")
    
    # Parse basic config fields
    quad_mask, asic_mask, run_delay, event_code = struct.unpack('<4I', data[0:16])
    
    return CSPadConfig(quad_mask, asic_mask, run_delay, event_code)


def parse_princeton_frame(data: bytes, version: int) -> CameraFrame:
    """
    Parse Princeton camera frame data.
    """
    if version == 1:
        if len(data) < 16:
            raise ValueError("Princeton frame header too short")
        
        # Princeton frame header
        shotIdStart, readoutTime = struct.unpack('<2I', data[0:8])
        width, height = struct.unpack('<2I', data[8:16])
        
        # Princeton uses 16-bit pixels
        pixel_data_size = width * height * 2
        
        if len(data) < 16 + pixel_data_size:
            raise ValueError(f"Princeton frame data too short")
        
        pixel_data = data[16:16 + pixel_data_size]
        pixels = np.frombuffer(pixel_data, dtype='<u2')
        image = pixels.reshape((height, width))
        
        return CameraFrame(width, height, 16, 0, image)
    
    else:
        raise ValueError(f"Unsupported Princeton version: {version}")


def parse_epix10ka2m_array(data: bytes, version: int) -> Epix10ka2MData:
    """
    Parse Epix10ka2M ArrayV1 data from XTC payload.
    
    Expected binary structure (based on psana DDL):
    - uint32_t frameNumber (4 bytes)
    - uint16_t frame[16][352][384] (16 * 352 * 384 * 2 bytes)
    - Additional calibration/environmental data (skipped in MVP)
    
    Args:
        data: Raw array data bytes
        version: Version from XTC header
        
    Returns:
        Parsed Epix10ka2M data
    """
    if len(data) < 4:
        raise ValueError("Epix10ka2M data too short for frame number")
    
    # Parse frame number (uint32)
    frame_number = struct.unpack('<I', data[0:4])[0]
    
    # Calculate expected frame data size
    # 16 panels × 352 rows × 384 columns × 2 bytes/pixel
    num_panels = 16
    panel_rows = 352
    panel_cols = 384
    bytes_per_pixel = 2
    frame_data_size = num_panels * panel_rows * panel_cols * bytes_per_pixel
    
    if len(data) < 4 + frame_data_size:
        raise ValueError(f"Epix10ka2M data too short: expected {4 + frame_data_size}, got {len(data)}")
    
    # Extract frame data (skip first 4 bytes which are frame number)
    frame_bytes = data[4:4 + frame_data_size]
    
    # Parse as uint16 array (little-endian)
    pixel_data = np.frombuffer(frame_bytes, dtype='<u2')
    
    # Reshape to (16, 352, 384)
    frames = pixel_data.reshape((num_panels, panel_rows, panel_cols))
    
    return Epix10ka2MData(frame_number, frames)


def parse_detector_data(data: bytes, type_id: int, version: int) -> Any:
    """
    Parse detector data based on type ID and version.
    
    Args:
        data: Raw detector data bytes
        type_id: Type ID from XTC header
        version: Version from XTC header
        
    Returns:
        Parsed detector data object (type depends on detector)
    """
    if type_id == TypeId.Id_Frame:
        return parse_camera_frame(data, type_id, version)
    
    elif type_id == TypeId.Id_pnCCDframe:
        return parse_pnccd_frame(data, version)
    
    elif type_id == TypeId.Id_CspadElement:
        return parse_cspad_element(data, version)
    
    elif type_id == TypeId.Id_CspadConfig:
        return parse_cspad_config(data, version)
    
    elif type_id == TypeId.Id_PrincetonFrame:
        return parse_princeton_frame(data, version)
    
    elif type_id == TypeId.Id_Epix10kaArray:
        return parse_epix10ka2m_array(data, version)
    
    elif type_id == TypeId.Id_Experimental_6193:
        # Experimental TypeId for Epix10ka2M array data (mfx100903824, old analysis)
        try:
            return parse_epix10ka2m_array(data, version)
        except Exception as e:
            print(f"Warning: Failed to parse experimental TypeId {type_id} as Epix10ka2M: {e}")
            return data
    
    elif type_id == TypeId.Id_Experimental_117:
        # Corrected experimental TypeId for Epix10ka2M detector data (~4.3MB)
        try:
            return parse_epix10ka2m_array(data, version)
        except Exception as e:
            print(f"Warning: Failed to parse experimental TypeId {type_id} as Epix10ka2M: {e}")
            return data
            
    elif type_id == TypeId.Id_Experimental_118:
        # Corrected experimental TypeId for Epix10ka2M detector data (~4.4MB)
        try:
            return parse_epix10ka2m_array(data, version)
        except Exception as e:
            print(f"Warning: Failed to parse experimental TypeId {type_id} as Epix10ka2M: {e}")
            return data
    
    else:
        # Return raw data for unsupported types
        return data


def get_detector_shape(type_id: int, version: int) -> Optional[tuple[int, ...]]:
    """
    Get expected data shape for detector type.
    
    Returns:
        Tuple of dimensions or None if unknown
    """
    shapes = {
        TypeId.Id_pnCCDframe: (512, 512),
        TypeId.Id_CspadElement: (185, 388),
        TypeId.Id_Epix10kaArray: (16, 352, 384),  # 16 panels of 352x384
        # Add more as needed
    }
    
    return shapes.get(type_id)


def is_image_type(type_id: int) -> bool:
    """
    Check if type ID represents image/detector data.
    """
    image_types = {
        TypeId.Id_Frame,
        TypeId.Id_pnCCDframe, 
        TypeId.Id_CspadElement,
        TypeId.Id_PrincetonFrame,
        TypeId.Id_Epix10kaArray,
        # Experimental TypeIds for Epix10ka2M 
        TypeId.Id_Experimental_6193,  # mfx100903824 Epix10ka2M array data (from old analysis)
        TypeId.Id_Experimental_117,   # mfx100903824 Epix10ka2M detector data (corrected)
        TypeId.Id_Experimental_118,   # mfx100903824 Epix10ka2M detector data (corrected)
        # Add more as needed
    }
    
    return type_id in image_types


def get_type_description(type_id: int) -> str:
    """
    Get human-readable description of data type.
    """
    descriptions = {
        TypeId.Id_Frame: "Generic camera frame",
        TypeId.Id_pnCCDframe: "pnCCD detector frame (512x512)",
        TypeId.Id_CspadElement: "CSPad 2x1 element (185x388)",
        TypeId.Id_CspadConfig: "CSPad configuration",
        TypeId.Id_PrincetonFrame: "Princeton camera frame",
        TypeId.Id_Epix10kaArray: "Epix10ka2M detector array (16x352x384)",
        TypeId.Id_Epix10ka2MConfig: "Epix10ka2M configuration",
        # Experimental TypeIds for specific experiments
        TypeId.Id_Experimental_6185: "Epix10ka2M config (experimental - mfx100903824)",
        TypeId.Id_Experimental_6190: "Epix10ka2M config v2 (experimental - mfx100903824)",
        TypeId.Id_Experimental_6193: "Epix10ka2M array data (experimental - mfx100903824, old analysis)",
        TypeId.Id_Experimental_117: "Epix10ka2M detector data (experimental - mfx100903824, ~4.3MB)",
        TypeId.Id_Experimental_118: "Epix10ka2M detector data (experimental - mfx100903824, ~4.4MB)",
        TypeId.Id_Xtc: "XTC container",
        TypeId.Id_EvrData: "Event receiver data",
        TypeId.Id_EBeam: "Electron beam data",
        TypeId.Id_Epics: "EPICS PV data",
    }
    
    return descriptions.get(type_id, f"Unknown type {type_id}")