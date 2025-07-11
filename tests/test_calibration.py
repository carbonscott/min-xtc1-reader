"""
Test suite for calibration system.

Tests all calibration functionality including pedestal subtraction,
common mode correction, pixel masking, and calibration file loading.
"""

import numpy as np
import tempfile
import shutil
from pathlib import Path
from typing import Tuple

from xtc1reader.calibration import (
    CalibrationConstants, DetectorCalibrator, CalibrationManager,
    CommonModeCorrection, create_default_calibration, calibrate_detector_data
)


def test_calibration_constants():
    """Test CalibrationConstants class"""
    print("Testing CalibrationConstants...")
    
    # Test basic creation
    constants = CalibrationConstants(
        detector_name="test_detector",
        run_number=123
    )
    
    assert constants.detector_name == "test_detector"
    assert constants.run_number == 123
    assert not constants.is_valid()  # No pedestals
    assert not constants.has_common_mode()
    assert not constants.has_pixel_status()
    
    # Test with pedestals
    pedestals = np.ones((10, 10)) * 100
    constants.pedestals = pedestals
    assert constants.is_valid()
    
    # Test with all data
    pixel_status = np.zeros((10, 10), dtype=np.uint8)
    common_mode = np.ones((10, 10), dtype=np.uint8)
    
    constants.pixel_status = pixel_status
    constants.common_mode = common_mode
    
    assert constants.has_pixel_status()
    assert constants.has_common_mode()
    
    print("✓ CalibrationConstants")


def test_common_mode_correction():
    """Test common mode correction algorithms"""
    print("Testing common mode correction...")
    
    # Create test data with known common mode
    data = np.random.normal(1000, 10, (100, 100))
    
    # Add global common mode offset
    common_offset = 50.0
    data += common_offset
    
    # Test median subtraction (global)
    corrected = CommonModeCorrection.median_subtraction(data)
    
    # Should remove most of the common offset
    median_before = np.median(data)
    median_after = np.median(corrected)
    
    assert abs(median_after) < abs(median_before)
    assert abs(median_after) < 5.0  # Should be close to zero
    
    # Test mean subtraction (global)
    corrected_mean = CommonModeCorrection.mean_subtraction(data)
    mean_after = np.mean(corrected_mean)
    assert abs(mean_after) < 5.0
    
    # Test regional common mode
    regions = np.zeros((100, 100), dtype=np.uint8)
    regions[:50, :] = 1  # Top half
    regions[50:, :] = 2  # Bottom half
    
    # Add different offsets to each region
    data_regional = data.copy()
    data_regional[:50, :] += 20.0   # Extra offset for region 1
    data_regional[50:, :] += -15.0  # Different offset for region 2
    
    corrected_regional = CommonModeCorrection.median_subtraction(data_regional, regions)
    
    # Check that each region is properly corrected
    region1_median = np.median(corrected_regional[:50, :])
    region2_median = np.median(corrected_regional[50:, :])
    
    assert abs(region1_median) < 5.0
    assert abs(region2_median) < 5.0
    
    print("✓ Common mode correction")


def test_detector_calibrator():
    """Test DetectorCalibrator class"""
    print("Testing DetectorCalibrator...")
    
    # Create test data
    shape = (50, 50)
    raw_data = np.random.normal(1100, 20, shape)
    
    # Create calibration constants
    pedestals = np.ones(shape) * 100
    pixel_status = np.zeros(shape, dtype=np.uint8)
    pixel_status[10, 10] = 1  # Mark one pixel as bad
    pixel_status[20, 20] = 2  # Mark another as bad (different status)
    
    # Create common mode regions
    common_mode = np.zeros(shape, dtype=np.uint8)
    common_mode[:25, :] = 1  # Top half
    common_mode[25:, :] = 2  # Bottom half
    
    constants = CalibrationConstants(
        detector_name="test",
        run_number=1,
        pedestals=pedestals,
        pixel_status=pixel_status,
        common_mode=common_mode
    )
    
    calibrator = DetectorCalibrator(constants)
    
    # Test pedestal subtraction
    corrected = calibrator.apply_pedestals(raw_data)
    expected_mean = np.mean(raw_data) - 100
    actual_mean = np.mean(corrected)
    assert abs(actual_mean - expected_mean) < 1.0
    
    # Test pixel masking
    masked = calibrator.apply_pixel_mask(raw_data)
    assert np.isnan(masked[10, 10])  # Bad pixel should be NaN
    assert np.isnan(masked[20, 20])  # Another bad pixel
    assert not np.isnan(masked[0, 0])  # Good pixel should not be NaN
    
    # Test common mode correction
    cm_corrected = calibrator.apply_common_mode(raw_data)
    assert cm_corrected.shape == raw_data.shape
    
    # Test full calibration pipeline
    fully_calibrated = calibrator.calibrate(raw_data)
    
    # Should be both pedestal and common mode corrected, so mean should be close to zero
    calibrated_mean = np.mean(fully_calibrated[~np.isnan(fully_calibrated)])
    assert abs(calibrated_mean) < 20  # Should be close to zero after all corrections
    
    # Bad pixels should be masked
    assert np.isnan(fully_calibrated[10, 10])
    assert np.isnan(fully_calibrated[20, 20])
    
    # Test selective application
    no_cm = calibrator.calibrate(raw_data, apply_common_mode=False)
    no_mask = calibrator.calibrate(raw_data, apply_pixel_mask=False)
    
    assert not np.isnan(no_mask[10, 10])  # Should not be masked
    
    print("✓ DetectorCalibrator")


def test_calibration_manager():
    """Test CalibrationManager with file loading"""
    print("Testing CalibrationManager...")
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        calib_dir = Path(temp_dir) / "calibration"
        detector_dir = calib_dir / "test_detector"
        
        # Create directory structure
        pedestals_dir = detector_dir / "pedestals"
        pixel_status_dir = detector_dir / "pixel_status"
        common_mode_dir = detector_dir / "common_mode"
        
        pedestals_dir.mkdir(parents=True)
        pixel_status_dir.mkdir(parents=True)
        common_mode_dir.mkdir(parents=True)
        
        # Create test calibration files
        shape = (20, 30)
        
        # Save pedestals (use .npy extension for np.save)
        pedestals = np.ones(shape) * 95.5
        pedestals_file = pedestals_dir / "run_0100.data"
        np.save(str(pedestals_file), pedestals)
        
        # Save pixel status  
        pixel_status = np.zeros(shape, dtype=np.uint8)
        pixel_status[5, 10] = 1
        pixel_status_file = pixel_status_dir / "run_0100.data"
        np.save(str(pixel_status_file), pixel_status)
        
        # Save common mode
        common_mode = np.ones(shape, dtype=np.uint8)
        common_mode_file = common_mode_dir / "run_0100.data"
        np.save(str(common_mode_file), common_mode)
        
        # Test CalibrationManager
        manager = CalibrationManager(calib_dir)
        
        # Load constants
        constants = manager.load_constants("test_detector", 100)
        assert constants is not None
        assert constants.detector_name == "test_detector"
        assert constants.run_number == 100
        assert constants.is_valid()
        assert constants.has_pixel_status()
        assert constants.has_common_mode()
        
        # Check loaded values
        assert np.allclose(constants.pedestals, 95.5)
        assert constants.pixel_status[5, 10] == 1
        assert np.all(constants.common_mode == 1)
        
        # Test getting calibrator
        calibrator = manager.get_calibrator("test_detector", 100)
        assert calibrator is not None
        
        # Test non-existent detector
        constants_missing = manager.load_constants("missing_detector", 100)
        assert constants_missing is None
        
        calibrator_missing = manager.get_calibrator("missing_detector", 100)
        assert calibrator_missing is None
        
        # Test caching (second call should use cache)
        constants2 = manager.load_constants("test_detector", 100)
        assert constants2 is constants  # Should be same object from cache
    
    print("✓ CalibrationManager")


def test_default_calibration():
    """Test default calibration creation"""
    print("Testing default calibration...")
    
    # Test 2D detector
    shape = (100, 200)
    constants = create_default_calibration("test_detector", shape, 42)
    
    assert constants.detector_name == "test_detector"
    assert constants.run_number == 42
    assert constants.is_valid()
    assert constants.has_pixel_status()
    assert constants.has_common_mode()
    
    # Check shapes
    assert constants.pedestals.shape == shape
    assert constants.pixel_status.shape == shape
    assert constants.common_mode.shape == shape
    
    # Check pedestal values are reasonable
    assert 80 < np.mean(constants.pedestals) < 120
    assert np.std(constants.pedestals) > 0  # Should have some variation
    
    # Check some pixels are marked as bad
    num_bad = np.sum(constants.pixel_status > 0)
    expected_bad = int(0.01 * np.prod(shape))  # ~1%
    assert 0 < num_bad <= expected_bad * 2  # Allow some variation
    
    # Check common mode regions
    assert np.min(constants.common_mode) >= 0
    assert np.max(constants.common_mode) > 0
    
    # Test 1D detector
    shape_1d = (1000,)
    constants_1d = create_default_calibration("test_1d", shape_1d, 1)
    assert constants_1d.pedestals.shape == shape_1d
    assert constants_1d.common_mode is None  # No common mode for 1D
    
    print("✓ Default calibration")


def test_convenience_function():
    """Test calibrate_detector_data convenience function"""
    print("Testing convenience function...")
    
    # Test with missing calibration (should use defaults)
    data = np.random.normal(1050, 15, (30, 40))
    
    calibrated = calibrate_detector_data(
        data, "test_detector", 123,
        calibration_dir=None  # No calibration directory
    )
    
    # Should return calibrated data
    assert calibrated.shape == data.shape
    assert not np.array_equal(calibrated, data)  # Should be different after calibration
    
    # Test with custom calibration directory
    with tempfile.TemporaryDirectory() as temp_dir:
        calib_dir = Path(temp_dir) / "calibration" 
        
        # Test with non-existent directory (should use defaults)
        calibrated2 = calibrate_detector_data(
            data, "test_detector", 123,
            calibration_dir=calib_dir
        )
        
        assert calibrated2.shape == data.shape
    
    print("✓ Convenience function")


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("Testing edge cases...")
    
    # Test with mismatched shapes
    data = np.ones((10, 10))
    pedestals = np.ones((5, 5))  # Wrong shape
    
    constants = CalibrationConstants(
        detector_name="test",
        run_number=1,
        pedestals=pedestals
    )
    
    calibrator = DetectorCalibrator(constants)
    
    try:
        calibrator.apply_pedestals(data)
        assert False, "Should have raised ValueError for shape mismatch"
    except ValueError:
        pass  # Expected
    
    # Test with invalid common mode algorithm
    try:
        calibrator.apply_common_mode(data, algorithm="invalid")
        assert False, "Should have raised ValueError for invalid algorithm"
    except ValueError:
        pass  # Expected
    
    # Test common mode with non-2D data
    data_1d = np.ones(100)
    try:
        CommonModeCorrection.median_subtraction(data_1d)
        assert False, "Should have raised ValueError for 1D data"
    except ValueError:
        pass  # Expected
    
    # Test with no calibration constants
    empty_constants = CalibrationConstants("test", 1)
    empty_calibrator = DetectorCalibrator(empty_constants)
    
    # Should return original data with warnings
    result = empty_calibrator.apply_pedestals(data)
    assert np.array_equal(result, data)
    
    print("✓ Edge cases")


def test_realistic_scenario():
    """Test realistic calibration scenario with CSPad-like data"""
    print("Testing realistic scenario...")
    
    # Simulate CSPad 2x1 segment data
    shape = (185, 388)  # Typical CSPad 2x1 shape
    
    # Create synthetic "raw" data
    # - Base signal around 1000 ADU
    # - Add pedestals around 100 ADU
    # - Add common mode noise
    # - Add some bad pixels
    
    np.random.seed(42)  # For reproducible results
    
    # Start with clean signal
    clean_signal = np.random.normal(50, 10, shape)  # Actual photon signal
    
    # Add pedestals (vary by pixel)
    pedestals_true = np.random.normal(100, 5, shape)
    
    # Add common mode (row-wise pattern)
    common_mode_pattern = np.random.normal(0, 3, shape[0])  # Per-row offset
    common_mode_2d = np.broadcast_to(common_mode_pattern[:, np.newaxis], shape)
    
    # Combine to create "raw" data
    raw_data = clean_signal + pedestals_true + common_mode_2d
    
    # Add some outliers (hot pixels, cosmic rays)
    hot_pixels = np.random.choice(np.prod(shape), 50, replace=False)
    flat_raw = raw_data.flatten()
    flat_raw[hot_pixels] += np.random.normal(500, 100, len(hot_pixels))
    raw_data = flat_raw.reshape(shape)
    
    # Create calibration constants (as if loaded from calibration system)
    pixel_status = np.zeros(shape, dtype=np.uint8)
    pixel_status.flat[hot_pixels[:25]] = 1  # Mark half the hot pixels as bad
    
    # Common mode regions (more realistic - group rows into larger regions)
    common_mode_regions = np.zeros(shape, dtype=np.uint8)
    rows_per_region = 10  # Group 10 rows per common mode region
    for i in range(shape[0]):
        region_id = (i // rows_per_region) + 1
        common_mode_regions[i, :] = region_id
    
    constants = CalibrationConstants(
        detector_name="cspad",
        run_number=137,
        pedestals=pedestals_true,  # Perfect pedestals
        pixel_status=pixel_status,
        common_mode=common_mode_regions
    )
    
    # Apply calibration
    calibrator = DetectorCalibrator(constants)
    calibrated = calibrator.calibrate(raw_data)
    
    # Verify calibration worked
    # 1. Pedestals should be subtracted
    # 2. Common mode should be reduced
    # 3. Bad pixels should be masked
    
    # Remove NaN pixels for analysis
    good_pixels = ~np.isnan(calibrated)
    
    # Should be closer to original clean signal than raw data
    clean_mean = np.mean(clean_signal[good_pixels])
    calibrated_mean = np.mean(calibrated[good_pixels])
    raw_mean = np.mean(raw_data[good_pixels])
    
    # After calibration should be closer to clean signal than raw data was
    clean_to_calibrated = abs(calibrated_mean - clean_mean)
    clean_to_raw = abs(raw_mean - clean_mean)
    
    assert clean_to_calibrated < clean_to_raw  # Should be improved
    
    # Standard deviation should be improved (less noise)
    original_std = np.std(raw_data[good_pixels])
    calibrated_std = np.std(calibrated[good_pixels])
    
    # After removing common mode, std should be smaller
    assert calibrated_std < original_std
    
    # Bad pixels should be masked
    assert np.sum(np.isnan(calibrated)) >= 25  # At least the marked bad pixels
    
    print("✓ Realistic scenario")


def run_all_calibration_tests():
    """Run all calibration tests"""
    print("Running Calibration System Tests...")
    print()
    
    try:
        test_calibration_constants()
        test_common_mode_correction()
        test_detector_calibrator()
        test_calibration_manager()
        test_default_calibration()
        test_convenience_function()
        test_edge_cases()
        test_realistic_scenario()
        
        print()
        print("✅ All calibration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Calibration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_calibration_tests()
    exit(0 if success else 1)