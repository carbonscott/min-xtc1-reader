"""
Test suite for the minimal geometry system.

Tests coordinate calculations, transformations, and image assembly.
"""

import sys
# Ensure we get the real numpy, not the local directory
import numpy as np
import tempfile
import os
from xtc1reader.geometry import (
    DetectorSegment, DetectorGeometry, CoordinateArrays,
    create_cspad_geometry, create_pnccd_geometry, create_camera_geometry,
    apply_rotation_2d, compute_segment_coordinates, compute_detector_coordinates,
    parse_geometry_file, assemble_image, get_detector_geometry,
    save_coordinate_arrays, load_coordinate_arrays
)


def test_detector_segment():
    """Test DetectorSegment creation and properties"""
    print("Testing DetectorSegment...")
    
    segment = DetectorSegment(
        index=0,
        shape=(100, 200),
        pixel_size_um=50.0,
        position_um=(1000.0, 2000.0, 3000.0),
        rotation_deg=90.0
    )
    
    assert segment.index == 0
    assert segment.shape == (100, 200)
    assert segment.pixel_size_um == 50.0
    assert segment.position_um == (1000.0, 2000.0, 3000.0)
    assert segment.rotation_deg == 90.0
    
    print("✓ DetectorSegment creation")


def test_detector_geometry():
    """Test DetectorGeometry creation and access"""
    print("Testing DetectorGeometry...")
    
    segments = [
        DetectorSegment(0, (100, 100), 50.0, (0, 0, 0), 0.0),
        DetectorSegment(1, (100, 100), 50.0, (5000, 0, 0), 90.0)
    ]
    
    geometry = DetectorGeometry("test_detector", segments)
    
    assert geometry.name == "test_detector"
    assert geometry.num_segments == 2
    assert geometry.get_segment(0).index == 0
    assert geometry.get_segment(1).rotation_deg == 90.0
    
    print("✓ DetectorGeometry creation")


def test_rotation_2d():
    """Test 2D rotation function"""
    print("Testing 2D rotation...")
    
    # Test 90-degree rotation
    x = np.array([1.0, 0.0])
    y = np.array([0.0, 1.0])
    
    x_rot, y_rot = apply_rotation_2d(x, y, 90.0)
    
    # After 90° rotation: (1,0) -> (0,1), (0,1) -> (-1,0)
    np.testing.assert_allclose(x_rot, [0.0, -1.0], atol=1e-10)
    np.testing.assert_allclose(y_rot, [1.0, 0.0], atol=1e-10)
    
    # Test 180-degree rotation
    x_rot, y_rot = apply_rotation_2d(x, y, 180.0)
    np.testing.assert_allclose(x_rot, [-1.0, 0.0], atol=1e-10)
    np.testing.assert_allclose(y_rot, [0.0, -1.0], atol=1e-10)
    
    print("✓ 2D rotation")


def test_segment_coordinates():
    """Test coordinate calculation for single segment"""
    print("Testing segment coordinates...")
    
    # Simple 3x3 segment, no rotation
    segment = DetectorSegment(
        index=0,
        shape=(3, 3),
        pixel_size_um=100.0,
        position_um=(1000.0, 2000.0, 3000.0),
        rotation_deg=0.0
    )
    
    x_coords, y_coords, z_coords = compute_segment_coordinates(segment)
    
    # Check shape
    assert x_coords.shape == (3, 3)
    assert y_coords.shape == (3, 3)
    assert z_coords.shape == (3, 3)
    
    # Check center pixel (should be at segment position)
    center_x = x_coords[1, 1]  # Middle pixel
    center_y = y_coords[1, 1]
    center_z = z_coords[1, 1]
    
    assert abs(center_x - 1000.0) < 1e-6
    assert abs(center_y - 2000.0) < 1e-6
    assert abs(center_z - 3000.0) < 1e-6
    
    # Check pixel spacing
    dx = x_coords[1, 2] - x_coords[1, 1]  # Adjacent pixels
    dy = y_coords[2, 1] - y_coords[1, 1]
    
    assert abs(dx - 100.0) < 1e-6  # Should equal pixel size
    assert abs(dy - 100.0) < 1e-6
    
    print("✓ Segment coordinates")


def test_detector_coordinates():
    """Test coordinate calculation for multi-segment detector"""
    print("Testing detector coordinates...")
    
    # Create simple 2-segment detector
    segments = [
        DetectorSegment(0, (2, 2), 100.0, (0, 0, 0), 0.0),
        DetectorSegment(1, (2, 2), 100.0, (300, 0, 0), 0.0)
    ]
    geometry = DetectorGeometry("test", segments)
    
    coords = compute_detector_coordinates(geometry)
    
    # Should have 2 segments
    assert coords.x_coords.shape == (2, 2, 2)
    assert coords.y_coords.shape == (2, 2, 2)
    assert coords.z_coords.shape == (2, 2, 2)
    
    # Check segment separation
    seg0_center_x = coords.x_coords[0, 1, 1]
    seg1_center_x = coords.x_coords[1, 1, 1]
    
    assert abs(seg1_center_x - seg0_center_x - 300.0) < 1e-6
    
    print("✓ Detector coordinates")


def test_predefined_geometries():
    """Test predefined detector geometries"""
    print("Testing predefined geometries...")
    
    # Test CSPad
    cspad_geom = create_cspad_geometry()
    assert cspad_geom.name == "cspad"
    assert cspad_geom.num_segments == 32
    assert cspad_geom.get_segment(0).shape == (185, 388)
    assert cspad_geom.get_segment(0).pixel_size_um == 109.92
    
    # Test pnCCD
    pnccd_geom = create_pnccd_geometry()
    assert pnccd_geom.name == "pnccd"
    assert pnccd_geom.num_segments == 1
    assert pnccd_geom.get_segment(0).shape == (512, 512)
    assert pnccd_geom.get_segment(0).pixel_size_um == 75.0
    
    # Test camera
    camera_geom = create_camera_geometry(640, 480, 24.0)
    assert camera_geom.name == "camera"
    assert camera_geom.num_segments == 1
    assert camera_geom.get_segment(0).shape == (480, 640)
    assert camera_geom.get_segment(0).pixel_size_um == 24.0
    
    print("✓ Predefined geometries")


def test_geometry_file_parsing():
    """Test parsing of geometry file format"""
    print("Testing geometry file parsing...")
    
    # Create test geometry file
    test_data = '''# Test geometry file
# Comment line
CSPAD:V2      0 SENS2X1:V1    0     1000   2000      100    90.0    0.0    0.0   0.1  0.2  0.3
CSPAD:V2      0 SENS2X1:V1    1     3000   4000      200     0.0    0.0    0.0   0.4  0.5  0.6
'''
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.data', delete=False) as f:
        f.write(test_data)
        temp_filename = f.name
    
    try:
        # Parse the file
        geometry = parse_geometry_file(temp_filename)
        
        assert geometry.name == "cspad"
        assert geometry.num_segments == 2
        
        seg0 = geometry.get_segment(0)
        assert seg0.index == 0
        assert seg0.position_um == (1000.0, 2000.0, 100.0)
        assert seg0.rotation_deg == 90.0
        assert seg0.shape == (185, 388)  # CSPad default
        
        seg1 = geometry.get_segment(1)
        assert seg1.index == 1
        assert seg1.position_um == (3000.0, 4000.0, 200.0)
        assert seg1.rotation_deg == 0.0
        
        print("✓ Geometry file parsing")
        
    finally:
        os.unlink(temp_filename)


def test_image_assembly():
    """Test image assembly from detector segments"""
    print("Testing image assembly...")
    
    # Create simple 2-segment detector with known data
    segments = [
        DetectorSegment(0, (2, 2), 100.0, (0, 0, 0), 0.0),
        DetectorSegment(1, (2, 2), 100.0, (250, 0, 0), 0.0)  # Adjacent segments
    ]
    geometry = DetectorGeometry("test", segments)
    
    # Create test data
    segment_data = np.array([
        [[10, 20], [30, 40]],  # Segment 0
        [[50, 60], [70, 80]]   # Segment 1
    ])
    
    # Assemble image
    assembled = assemble_image(segment_data, geometry)
    
    # Should produce a single image
    assert assembled.ndim == 2
    assert assembled.shape[0] > 0
    assert assembled.shape[1] > 0
    
    # Check that data is preserved (non-zero)
    assert np.sum(assembled) > 0
    
    print("✓ Image assembly")


def test_coordinate_save_load():
    """Test saving and loading coordinate arrays"""
    print("Testing coordinate save/load...")
    
    # Create test coordinates
    x_coords = np.random.rand(2, 3, 4)
    y_coords = np.random.rand(2, 3, 4)
    z_coords = np.random.rand(2, 3, 4)
    pixel_areas = np.random.rand(2, 3, 4)
    
    coords = CoordinateArrays(x_coords, y_coords, z_coords, pixel_areas)
    
    # Save to temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        save_coordinate_arrays(coords, temp_dir, "test")
        
        # Load back
        loaded_coords = load_coordinate_arrays(temp_dir, "test")
        
        # Check equality
        np.testing.assert_array_equal(coords.x_coords, loaded_coords.x_coords)
        np.testing.assert_array_equal(coords.y_coords, loaded_coords.y_coords)
        np.testing.assert_array_equal(coords.z_coords, loaded_coords.z_coords)
        np.testing.assert_array_equal(coords.pixel_areas, loaded_coords.pixel_areas)
    
    print("✓ Coordinate save/load")


def test_get_detector_geometry():
    """Test detector geometry factory function"""
    print("Testing detector geometry factory...")
    
    # Test predefined detectors
    cspad = get_detector_geometry("cspad")
    assert cspad.name == "cspad"
    assert cspad.num_segments == 32
    
    pnccd = get_detector_geometry("pnccd")
    assert pnccd.name == "pnccd"
    assert pnccd.num_segments == 1
    
    # Test camera with parameters
    camera = get_detector_geometry("camera", width=800, height=600, pixel_size_um=20.0)
    assert camera.name == "camera"
    assert camera.get_segment(0).shape == (600, 800)
    assert camera.get_segment(0).pixel_size_um == 20.0
    
    # Test unknown detector
    try:
        get_detector_geometry("unknown")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    print("✓ Detector geometry factory")


def test_coordinate_arrays():
    """Test CoordinateArrays named tuple"""
    print("Testing CoordinateArrays...")
    
    x = np.random.rand(3, 4)
    y = np.random.rand(3, 4)
    z = np.random.rand(3, 4)
    
    coords = CoordinateArrays(x, y, z)
    
    assert np.array_equal(coords.x_coords, x)
    assert np.array_equal(coords.y_coords, y)
    assert np.array_equal(coords.z_coords, z)
    assert coords.pixel_areas is None
    
    # Test with pixel areas
    areas = np.random.rand(3, 4)
    coords_with_areas = CoordinateArrays(x, y, z, areas)
    assert np.array_equal(coords_with_areas.pixel_areas, areas)
    
    print("✓ CoordinateArrays")


def run_all_geometry_tests():
    """Run all geometry tests"""
    print("Running Geometry System Tests...\n")
    
    try:
        test_detector_segment()
        test_detector_geometry()
        test_rotation_2d()
        test_segment_coordinates()
        test_detector_coordinates()
        test_predefined_geometries()
        test_geometry_file_parsing()
        test_image_assembly()
        test_coordinate_save_load()
        test_get_detector_geometry()
        test_coordinate_arrays()
        
        print("\n✅ All geometry tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Geometry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = run_all_geometry_tests()
    sys.exit(0 if success else 1)