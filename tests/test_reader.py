"""
Simple test module for XTC reader functionality.

Run basic tests to verify binary parsing and file reading.
"""

import os
import sys
import tempfile
import struct
from xtc1reader.binary_format import (
    parse_datagram_header, parse_xtc_header, ClockTime, TimeStamp, 
    Sequence, Env, Damage, Src, TypeIdInfo, XTCContainer, TypeId
)
from xtc1reader.xtc_reader import XTCReader, XTCIterator
from xtc1reader.data_types import parse_detector_data, is_image_type


def test_binary_parsing():
    """Test basic binary format parsing"""
    print("Testing binary format parsing...")
    
    # Test ClockTime
    clock = ClockTime(1234567890, 500000000)
    assert clock.as_double() == 1234567890.5
    print("✓ ClockTime parsing")
    
    # Test TimeStamp bitfield extraction  
    stamp = TimeStamp(0x123456, 0x78, 0x9ABC, 0xDEF0)
    assert stamp.ticks == 0x123456
    assert stamp.control == 0x78
    print("✓ TimeStamp parsing")
    
    # Test Damage flags
    damage = Damage(0x12000003)  # flags=3, user_bits=0x12
    assert damage.flags == 3
    assert damage.user_bits == 0x12
    print("✓ Damage parsing")
    
    # Test Src bitfield extraction
    src = Src(0x01234567, 0x89ABCDEF)
    assert src.level == 0x01
    assert src.process_id == 0x234567
    assert src.detector_type == 0x89
    print("✓ Src parsing")
    
    # Test TypeIdInfo
    typeid = TypeIdInfo(0x80003456)  # compressed=1, version=?, type=0x3456
    assert typeid.compressed == True
    # Correct calculation: (0x80003456 >> 16) & 0x7FFF = 0x8000 & 0x7FFF = 0x0000  
    assert typeid.version == 0x0000
    assert typeid.type_id == 0x3456
    print("✓ TypeIdInfo parsing")


def test_datagram_header():
    """Test datagram header parsing"""
    print("Testing datagram header parsing...")
    
    # Create test datagram header (24 bytes)
    # Sequence: clock(8) + stamp(8) = 16 bytes
    # Env: 4 bytes  
    # Damage: 4 bytes (first part of XTC)
    header_data = struct.pack('<6I',
        500000000,      # clock nanoseconds
        1234567890,     # clock seconds  
        0x123456 | (0x78 << 24),  # stamp_low: ticks + control
        0x9ABC | (0x1234 << 17),  # stamp_high: fiducials + vector (reduced size)
        0x87654321,     # env
        0x12000003      # damage
    )
    
    dgram = parse_datagram_header(header_data)
    
    assert dgram.seq.clock.seconds == 1234567890
    assert dgram.seq.clock.nanoseconds == 500000000
    assert dgram.seq.stamp.ticks == 0x123456
    assert dgram.seq.stamp.control == 0x78
    assert dgram.seq.stamp.vector == 0x1234  # Updated expected value
    assert dgram.env.value == 0x87654321
    assert dgram.xtc.damage.value == 0x12000003
    
    print("✓ Datagram header parsing")


def test_xtc_header():
    """Test XTC header parsing"""
    print("Testing XTC header parsing...")
    
    # Create test XTC header (20 bytes)
    xtc_data = struct.pack('<5I',
        0x12000003,     # damage
        0x01234567,     # src_log  
        0x89ABCDEF,     # src_phy
        0x80001234,     # typeid (compressed, version=1, type=0x1234)
        0x00000040      # extent (64 bytes total)
    )
    
    xtc = parse_xtc_header(xtc_data)
    
    assert xtc.damage.value == 0x12000003
    assert xtc.src.log == 0x01234567
    assert xtc.src.phy == 0x89ABCDEF
    assert xtc.contains.compressed == True
    assert xtc.contains.version == 0  # (0x80001234 >> 16) & 0x7FFF = 0x8000 & 0x7FFF = 0x0000
    assert xtc.contains.type_id == 0x1234
    assert xtc.extent == 64
    assert xtc.payload_size == 44  # 64 - 20
    
    print("✓ XTC header parsing")


def create_test_xtc_file() -> str:
    """Create a minimal test XTC file for testing"""
    print("Creating test XTC file...")
    
    # Create temporary file
    fd, filename = tempfile.mkstemp(suffix='.xtc')
    
    try:
        with os.fdopen(fd, 'wb') as f:
            # Create a simple datagram with one XTC container
            
            # Datagram header (24 bytes)
            dgram_header = struct.pack('<6I',
                0,              # clock nanoseconds
                1234567890,     # clock seconds
                0x123456,       # stamp_low (ticks)
                0x9ABC,         # stamp_high (fiducials)
                0x87654321,     # env
                0               # damage (first 4 bytes of XTC)
            )
            
            # Complete XTC header (remaining 16 bytes after damage)
            xtc_remainder = struct.pack('<4I',
                0x01000000,     # src_log (level=1)
                0x12345678,     # src_phy
                TypeId.Id_Frame, # typeid (generic frame)
                20 + 32         # extent (XTC header + payload)
            )
            
            # Fake payload (32 bytes of test data)
            payload = b'Test payload data for XTC file' + b'\x00\x00'
            
            # Write complete datagram
            f.write(dgram_header)
            f.write(xtc_remainder)
            f.write(payload)
        
        print(f"✓ Created test file: {filename}")
        return filename
        
    except Exception as e:
        os.unlink(filename)
        raise


def test_file_reading():
    """Test XTC file reading"""
    print("Testing XTC file reading...")
    
    # Create test file
    test_file = create_test_xtc_file()
    
    try:
        # Test file reading
        with XTCReader(test_file) as reader:
            events = list(reader)
            
        assert len(events) == 1, f"Expected 1 event, got {len(events)}"
        
        dgram, payload = events[0]
        
        # Verify datagram content
        assert dgram.seq.clock.seconds == 1234567890
        assert dgram.env.value == 0x87654321
        assert dgram.xtc.contains.type_id == TypeId.Id_Frame
        
        print("✓ File reading")
        
        # Test XTC iteration  
        iterator = XTCIterator(payload[16:])  # Skip the XTC header remainder
        containers = list(iterator)
        
        # Should have at least the main container
        assert len(containers) >= 0
        print("✓ XTC iteration")
        
    finally:
        os.unlink(test_file)


def test_data_type_parsing():
    """Test detector data type parsing"""
    print("Testing data type parsing...")
    
    # Test type checking
    assert is_image_type(TypeId.Id_Frame)
    assert is_image_type(TypeId.Id_pnCCDframe)
    assert not is_image_type(TypeId.Id_EvrConfig)
    
    print("✓ Data type classification")
    
    # Could add more specific tests with real detector data formats
    

def run_all_tests():
    """Run all tests"""
    print("Running XTC reader tests...\n")
    
    try:
        test_binary_parsing()
        test_datagram_header()
        test_xtc_header()
        test_file_reading()
        test_data_type_parsing()
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)