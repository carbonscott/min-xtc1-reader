"""
Minimal calibration system for LCLS detectors.

Provides essential calibration corrections without the complexity of the full
calibration infrastructure. Focuses on practical corrections needed for
basic analysis.
"""

import numpy as np
import os
from typing import Dict, List, Tuple, Optional, NamedTuple, TYPE_CHECKING, Union
from dataclasses import dataclass
from pathlib import Path
import warnings

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass
class CalibrationConstants:
    """
    Container for calibration constants for a single detector.
    """
    detector_name: str                    # Detector identifier (e.g., "cspad", "pnccd")
    run_number: int                      # Run number these constants apply to
    pedestals: Optional['NDArray'] = None        # Pedestal values per pixel
    pixel_status: Optional['NDArray'] = None     # Pixel status mask (0=good, >0=bad)
    common_mode: Optional['NDArray'] = None      # Common mode regions/parameters
    gain: Optional['NDArray'] = None             # Gain correction per pixel
    
    def is_valid(self) -> bool:
        """Check if calibration constants are valid and complete"""
        return self.pedestals is not None
    
    def has_common_mode(self) -> bool:
        """Check if common mode correction data is available"""
        return self.common_mode is not None
    
    def has_pixel_status(self) -> bool:
        """Check if pixel status mask is available"""
        return self.pixel_status is not None


@dataclass
class CalibrationMetadata:
    """
    Metadata about calibration constants.
    """
    detector_name: str
    run_range: Tuple[int, int]           # (min_run, max_run) 
    created_date: str
    version: str = "1.0"
    description: str = ""


class CommonModeCorrection:
    """
    Common mode correction algorithms for different detector types.
    
    Common mode is the correlated noise that affects multiple pixels
    simultaneously, typically from electronic readout.
    """
    
    @staticmethod
    def median_subtraction(data: 'NDArray', regions: Optional['NDArray'] = None,
                          threshold: float = 3.0) -> 'NDArray':
        """
        Median-based common mode correction.
        
        Args:
            data: Raw detector data (2D array)
            regions: Region map for common mode groups (same shape as data)
            threshold: Outlier rejection threshold in standard deviations
            
        Returns:
            Corrected data
        """
        if data.ndim != 2:
            raise ValueError("Data must be 2D array")
        
        corrected = data.copy()
        
        if regions is None:
            # Apply global common mode
            median_val = np.median(data)
            corrected -= median_val
        else:
            # Apply per-region common mode
            unique_regions = np.unique(regions)
            for region_id in unique_regions:
                if region_id == 0:  # Skip region 0 (usually means no correction)
                    continue
                    
                mask = regions == region_id
                region_data = data[mask]
                
                if len(region_data) < 10:  # Skip regions with too few pixels
                    continue
                
                # Robust median with outlier rejection
                median_val = np.median(region_data)
                std_val = np.std(region_data)
                
                # Remove outliers and recalculate
                good_pixels = np.abs(region_data - median_val) < threshold * std_val
                if np.sum(good_pixels) > 5:
                    median_val = np.median(region_data[good_pixels])
                
                corrected[mask] -= median_val
        
        return corrected
    
    @staticmethod
    def mean_subtraction(data: 'NDArray', regions: Optional['NDArray'] = None,
                        threshold: float = 3.0) -> 'NDArray':
        """
        Mean-based common mode correction (alternative to median).
        
        Args:
            data: Raw detector data (2D array)
            regions: Region map for common mode groups
            threshold: Outlier rejection threshold in standard deviations
            
        Returns:
            Corrected data
        """
        if data.ndim != 2:
            raise ValueError("Data must be 2D array")
        
        corrected = data.copy()
        
        if regions is None:
            # Apply global common mode
            mean_val = np.mean(data)
            corrected -= mean_val
        else:
            # Apply per-region common mode
            unique_regions = np.unique(regions)
            for region_id in unique_regions:
                if region_id == 0:
                    continue
                    
                mask = regions == region_id
                region_data = data[mask]
                
                if len(region_data) < 10:
                    continue
                
                # Robust mean with outlier rejection
                mean_val = np.mean(region_data)
                std_val = np.std(region_data)
                
                # Remove outliers and recalculate
                good_pixels = np.abs(region_data - mean_val) < threshold * std_val
                if np.sum(good_pixels) > 5:
                    mean_val = np.mean(region_data[good_pixels])
                
                corrected[mask] -= mean_val
        
        return corrected


class DetectorCalibrator:
    """
    Main calibration class that applies corrections to detector data.
    """
    
    def __init__(self, constants: CalibrationConstants):
        """
        Initialize calibrator with calibration constants.
        
        Args:
            constants: CalibrationConstants object
        """
        self.constants = constants
        
        if not constants.is_valid():
            warnings.warn(f"Calibration constants for {constants.detector_name} "
                         f"run {constants.run_number} are incomplete")
    
    def apply_pedestals(self, data: 'NDArray') -> 'NDArray':
        """
        Apply pedestal subtraction.
        
        Args:
            data: Raw detector data
            
        Returns:
            Pedestal-corrected data
        """
        if self.constants.pedestals is None:
            warnings.warn("No pedestal data available, skipping correction")
            return data.copy()
        
        if data.shape != self.constants.pedestals.shape:
            raise ValueError(f"Data shape {data.shape} doesn't match "
                           f"pedestal shape {self.constants.pedestals.shape}")
        
        return data - self.constants.pedestals
    
    def apply_pixel_mask(self, data: 'NDArray', mask_value: float = np.nan) -> 'NDArray':
        """
        Apply pixel status mask to mark bad pixels.
        
        Args:
            data: Detector data
            mask_value: Value to assign to bad pixels (default: NaN)
            
        Returns:
            Masked data
        """
        if self.constants.pixel_status is None:
            return data.copy()
        
        if data.shape != self.constants.pixel_status.shape:
            raise ValueError(f"Data shape {data.shape} doesn't match "
                           f"pixel status shape {self.constants.pixel_status.shape}")
        
        corrected = data.copy()
        bad_pixels = self.constants.pixel_status > 0
        corrected[bad_pixels] = mask_value
        
        return corrected
    
    def apply_common_mode(self, data: 'NDArray', algorithm: str = "median") -> 'NDArray':
        """
        Apply common mode correction.
        
        Args:
            data: Detector data
            algorithm: Algorithm to use ("median" or "mean")
            
        Returns:
            Common mode corrected data
        """
        if algorithm == "median":
            return CommonModeCorrection.median_subtraction(data, self.constants.common_mode)
        elif algorithm == "mean":
            return CommonModeCorrection.mean_subtraction(data, self.constants.common_mode)
        else:
            raise ValueError(f"Unknown common mode algorithm: {algorithm}")
    
    def calibrate(self, data: 'NDArray', 
                  apply_pedestals: bool = True,
                  apply_common_mode: bool = True,
                  apply_pixel_mask: bool = True,
                  common_mode_algorithm: str = "median") -> 'NDArray':
        """
        Apply all calibration corrections in the proper order.
        
        Standard order:
        1. Pedestal subtraction
        2. Common mode correction  
        3. Pixel masking
        
        Args:
            data: Raw detector data
            apply_pedestals: Apply pedestal correction
            apply_common_mode: Apply common mode correction
            apply_pixel_mask: Apply pixel status mask
            common_mode_algorithm: Algorithm for common mode ("median" or "mean")
            
        Returns:
            Fully calibrated data
        """
        result = data.copy()
        
        # Step 1: Pedestal subtraction
        if apply_pedestals:
            result = self.apply_pedestals(result)
        
        # Step 2: Common mode correction
        if apply_common_mode and self.constants.has_common_mode():
            result = self.apply_common_mode(result, common_mode_algorithm)
        
        # Step 3: Pixel masking (done last to preserve NaN propagation)
        if apply_pixel_mask and self.constants.has_pixel_status():
            result = self.apply_pixel_mask(result)
        
        return result


class CalibrationManager:
    """
    Manages calibration constants for multiple detectors and run ranges.
    """
    
    def __init__(self, calibration_dir: Optional[Union[str, Path]] = None):
        """
        Initialize calibration manager.
        
        Args:
            calibration_dir: Directory containing calibration files
        """
        self.calibration_dir = Path(calibration_dir) if calibration_dir else None
        self._constants_cache: Dict[Tuple[str, int], CalibrationConstants] = {}
    
    def load_constants(self, detector_name: str, run_number: int) -> Optional[CalibrationConstants]:
        """
        Load calibration constants for a specific detector and run.
        
        Args:
            detector_name: Name of detector (e.g., "cspad", "pnccd")
            run_number: Run number
            
        Returns:
            CalibrationConstants object or None if not found
        """
        cache_key = (detector_name, run_number)
        
        # Check cache first
        if cache_key in self._constants_cache:
            return self._constants_cache[cache_key]
        
        # Try to load from files
        constants = None
        if self.calibration_dir and self.calibration_dir.exists():
            constants = self._load_from_directory(detector_name, run_number)
        
        # Cache the result (even if None)
        self._constants_cache[cache_key] = constants
        return constants
    
    def _load_from_directory(self, detector_name: str, run_number: int) -> Optional[CalibrationConstants]:
        """
        Load constants from calibration directory structure.
        
        Expected structure:
        calibration_dir/
        ├── detector_name/
        │   ├── pedestals/
        │   │   └── run_XXXX.data
        │   ├── pixel_status/
        │   │   └── run_XXXX.data
        │   └── common_mode/
        │       └── run_XXXX.data
        """
        detector_dir = self.calibration_dir / detector_name
        if not detector_dir.exists():
            return None
        
        # Load pedestals (required)
        pedestals_file = detector_dir / "pedestals" / f"run_{run_number:04d}.data"
        
        # Check for .npy version first
        pedestals_npy_file = pedestals_file.with_suffix('.data.npy')
        if pedestals_npy_file.exists():
            pedestals_file = pedestals_npy_file
        elif not pedestals_file.exists():
            # Try finding closest run number
            pedestals_file = self._find_closest_calibration_file(
                detector_dir / "pedestals", run_number)
        
        if not pedestals_file or not pedestals_file.exists():
            return None
        
        try:
            pedestals = self._load_data_file(pedestals_file)
        except Exception as e:
            warnings.warn(f"Failed to load pedestals from {pedestals_file}: {e}")
            return None
        
        # Load optional files
        pixel_status = None
        pixel_status_file = detector_dir / "pixel_status" / f"run_{run_number:04d}.data"
        pixel_status_npy_file = pixel_status_file.with_suffix('.data.npy')
        
        if pixel_status_npy_file.exists():
            try:
                pixel_status = self._load_data_file(pixel_status_npy_file)
            except Exception as e:
                warnings.warn(f"Failed to load pixel status from {pixel_status_npy_file}: {e}")
        elif pixel_status_file.exists():
            try:
                pixel_status = self._load_data_file(pixel_status_file)
            except Exception as e:
                warnings.warn(f"Failed to load pixel status from {pixel_status_file}: {e}")
        
        common_mode = None
        common_mode_file = detector_dir / "common_mode" / f"run_{run_number:04d}.data"
        common_mode_npy_file = common_mode_file.with_suffix('.data.npy')
        
        if common_mode_npy_file.exists():
            try:
                common_mode = self._load_data_file(common_mode_npy_file)
            except Exception as e:
                warnings.warn(f"Failed to load common mode from {common_mode_npy_file}: {e}")
        elif common_mode_file.exists():
            try:
                common_mode = self._load_data_file(common_mode_file)
            except Exception as e:
                warnings.warn(f"Failed to load common mode from {common_mode_file}: {e}")
        
        return CalibrationConstants(
            detector_name=detector_name,
            run_number=run_number,
            pedestals=pedestals,
            pixel_status=pixel_status,
            common_mode=common_mode
        )
    
    def _find_closest_calibration_file(self, directory: Path, run_number: int) -> Optional[Path]:
        """Find calibration file with closest run number"""
        if not directory.exists():
            return None
        
        run_files = list(directory.glob("run_*.data"))
        if not run_files:
            return None
        
        # Extract run numbers and find closest
        run_numbers = []
        for f in run_files:
            try:
                run_num = int(f.stem.split('_')[1])
                run_numbers.append((abs(run_num - run_number), f))
            except (ValueError, IndexError):
                continue
        
        if not run_numbers:
            return None
        
        # Return file with closest run number
        run_numbers.sort(key=lambda x: x[0])
        return run_numbers[0][1]
    
    def _load_data_file(self, file_path: Path) -> 'NDArray':
        """
        Load data from .data file.
        
        Supports both binary and text formats commonly used in LCLS.
        """
        # Check if there's a .npy file with .data extension
        npy_file = file_path.with_suffix('.data.npy')
        if npy_file.exists():
            try:
                return np.load(npy_file)
            except:
                pass
        
        try:
            # Try numpy binary format first
            return np.load(file_path)
        except:
            pass
        
        try:
            # Try text format
            return np.loadtxt(file_path)
        except:
            pass
        
        try:
            # Try raw binary (assume float32)
            return np.fromfile(file_path, dtype=np.float32)
        except:
            pass
        
        raise ValueError(f"Could not load data from {file_path}")
    
    def get_calibrator(self, detector_name: str, run_number: int) -> Optional[DetectorCalibrator]:
        """
        Get a calibrator for specific detector and run.
        
        Args:
            detector_name: Name of detector
            run_number: Run number
            
        Returns:
            DetectorCalibrator instance or None if constants not available
        """
        constants = self.load_constants(detector_name, run_number)
        if constants is None:
            return None
        
        return DetectorCalibrator(constants)


def create_default_calibration(detector_name: str, shape: Tuple[int, ...], 
                              run_number: int = 1) -> CalibrationConstants:
    """
    Create default calibration constants for testing or when real calibration
    is not available.
    
    Args:
        detector_name: Name of detector
        shape: Shape of detector data
        run_number: Run number
        
    Returns:
        CalibrationConstants with default values
    """
    # Default pedestals (small random values around 100 ADU)
    pedestals = np.random.normal(100.0, 5.0, shape).astype(np.float32)
    
    # Default pixel status (mark 1% of pixels as bad randomly)
    pixel_status = np.zeros(shape, dtype=np.uint8)
    bad_fraction = 0.01
    num_bad = int(np.prod(shape) * bad_fraction)
    if num_bad > 0:
        flat_indices = np.random.choice(np.prod(shape), num_bad, replace=False)
        np.put(pixel_status, flat_indices, 1)
    
    # Default common mode regions (simple row-based for 2D detectors)
    common_mode = None
    if len(shape) == 2:
        common_mode = np.zeros(shape, dtype=np.uint8)
        # Group rows to avoid uint8 overflow (max 255 regions)
        max_regions = 254  # Leave room for 0 = no correction
        rows_per_region = max(1, shape[0] // max_regions)
        for i in range(shape[0]):
            region_id = (i // rows_per_region) + 1
            region_id = min(region_id, max_regions)  # Ensure no overflow
            common_mode[i, :] = region_id
    
    return CalibrationConstants(
        detector_name=detector_name,
        run_number=run_number,
        pedestals=pedestals,
        pixel_status=pixel_status,
        common_mode=common_mode
    )


def calibrate_detector_data(data: 'NDArray', detector_name: str, run_number: int,
                           calibration_dir: Optional[Union[str, Path]] = None,
                           **kwargs) -> 'NDArray':
    """
    Convenience function to calibrate detector data with automatic constant loading.
    
    Args:
        data: Raw detector data
        detector_name: Name of detector
        run_number: Run number
        calibration_dir: Directory containing calibration files
        **kwargs: Additional arguments passed to calibrate()
        
    Returns:
        Calibrated data
    """
    manager = CalibrationManager(calibration_dir)
    calibrator = manager.get_calibrator(detector_name, run_number)
    
    if calibrator is None:
        warnings.warn(f"No calibration found for {detector_name} run {run_number}, "
                     "using default calibration")
        constants = create_default_calibration(detector_name, data.shape, run_number)
        calibrator = DetectorCalibrator(constants)
    
    return calibrator.calibrate(data, **kwargs)