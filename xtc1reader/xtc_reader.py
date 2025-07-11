"""
XTC file reader with sequential datagram iteration and recursive parsing.

Provides the main XTCReader class for reading LCLS1 XTC files.
"""

import os
from typing import Iterator, List, Optional, BinaryIO
from .binary_format import (
    Datagram, XTCContainer, parse_datagram_header, 
    complete_datagram_with_xtc, parse_xtc_header, TypeId
)


class XTCReader:
    """
    Sequential reader for LCLS1 XTC files.
    
    Usage:
        reader = XTCReader('data.xtc')
        for dgram, payload in reader:
            print(f"Event at {dgram.seq.clock.as_double():.6f} seconds")
            # Process dgram and payload...
    """
    
    def __init__(self, filename: str):
        """
        Initialize XTC reader for given file.
        
        Args:
            filename: Path to XTC file to read
        """
        self.filename = filename
        self._fd: Optional[BinaryIO] = None
        self._file_size = os.path.getsize(filename)
        self._bytes_read = 0
        
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def open(self):
        """Open the XTC file for reading"""
        if self._fd is not None:
            return
        self._fd = open(self.filename, 'rb')
        self._bytes_read = 0
        
    def close(self):
        """Close the XTC file"""
        if self._fd is not None:
            self._fd.close()
            self._fd = None
            
    def __iter__(self) -> Iterator[tuple[Datagram, bytes]]:
        """Iterate over datagrams in the file"""
        if self._fd is None:
            self.open()
            
        return self._read_datagrams()
    
    def _read_datagrams(self) -> Iterator[tuple[Datagram, bytes]]:
        """Generator that yields (datagram, payload) tuples"""
        while self._bytes_read < self._file_size:
            try:
                # Read 24-byte datagram header
                header_data = self._fd.read(24)
                if len(header_data) < 24:
                    break  # End of file
                    
                self._bytes_read += 24
                
                # Parse partial datagram (missing 12 bytes of XTC header)
                partial_dgram = parse_datagram_header(header_data)
                
                # Read first 16 bytes to complete XTC header (20 total - 4 damage already read)
                xtc_header_data = self._fd.read(16)
                if len(xtc_header_data) < 16:
                    raise ValueError("Incomplete XTC header")
                    
                self._bytes_read += 16
                
                # Complete the datagram with full XTC info
                dgram = complete_datagram_with_xtc(partial_dgram, xtc_header_data)
                
                # Read remaining payload
                payload_size = dgram.xtc.payload_size
                if payload_size > 0:
                    payload_data = self._fd.read(payload_size)
                    if len(payload_data) < payload_size:
                        raise ValueError(f"Incomplete payload: {len(payload_data)} < {payload_size}")
                    self._bytes_read += payload_size
                else:
                    payload_data = b''
                
                # Combine XTC header remainder with payload
                full_payload = xtc_header_data + payload_data
                
                yield dgram, full_payload
                
            except Exception as e:
                print(f"Error reading datagram at byte {self._bytes_read}: {e}")
                break
    
    @property
    def progress(self) -> float:
        """Reading progress as fraction 0.0 to 1.0"""
        if self._file_size == 0:
            return 1.0
        return min(1.0, self._bytes_read / self._file_size)


class XTCIterator:
    """
    Recursive iterator for XTC containers within a payload.
    
    Handles nested XTC structures and yields individual containers.
    """
    
    def __init__(self, payload: bytes, start_offset: int = 0):
        """
        Initialize iterator for XTC payload data.
        
        Args:
            payload: Raw payload bytes containing XTC containers
            start_offset: Byte offset to start parsing from
        """
        self.payload = payload
        self.offset = start_offset
        
    def __iter__(self) -> Iterator[tuple[XTCContainer, bytes]]:
        """Iterate over XTC containers in payload"""
        return self._parse_containers()
    
    def _parse_containers(self) -> Iterator[tuple[XTCContainer, bytes]]:
        """Generator that yields (container, data) tuples"""
        while self.offset + 20 <= len(self.payload):
            try:
                # Parse XTC container header
                xtc = parse_xtc_header(self.payload, self.offset)
                
                # Extract container payload
                data_start = self.offset + 20
                data_end = self.offset + xtc.extent
                
                if data_end > len(self.payload):
                    print(f"Warning: XTC extent {xtc.extent} exceeds payload at offset {self.offset}")
                    break
                
                container_data = self.payload[data_start:data_end]
                
                yield xtc, container_data
                
                # Move to next container
                self.offset = data_end
                
            except Exception as e:
                print(f"Error parsing XTC at offset {self.offset}: {e}")
                break


def walk_xtc_tree(payload: bytes, level: int = 0, max_level: int = 10) -> List[tuple[int, XTCContainer, bytes]]:
    """
    Recursively walk XTC tree structure and return all containers.
    
    Args:
        payload: XTC payload bytes
        level: Current recursion level (for indentation)
        max_level: Maximum recursion depth to prevent infinite loops
        
    Returns:
        List of (level, container, data) tuples
    """
    results = []
    
    if level > max_level:
        return results
    
    iterator = XTCIterator(payload)
    
    for xtc, data in iterator:
        results.append((level, xtc, data))
        
        # If this is a container type, recurse into it
        if xtc.contains.type_id == TypeId.Id_Xtc:
            child_results = walk_xtc_tree(data, level + 1, max_level)
            results.extend(child_results)
    
    return results


def print_xtc_tree(payload: bytes, max_level: int = 5):
    """
    Print a human-readable tree view of XTC structure.
    
    Args:
        payload: XTC payload bytes
        max_level: Maximum recursion depth
    """
    tree = walk_xtc_tree(payload, max_level=max_level)
    
    for level, xtc, data in tree:
        indent = "  " * level
        type_name = xtc.contains.type_id.name if hasattr(xtc.contains.type_id, 'name') else f"Type_{xtc.contains.type_id}"
        
        print(f"{indent}{type_name} v{xtc.contains.version} "
              f"[{xtc.extent} bytes] "
              f"src=0x{xtc.src.log:08x}:0x{xtc.src.phy:08x} "
              f"damage=0x{xtc.damage.value:08x}")


# Convenience functions

def read_xtc_file(filename: str, max_events: Optional[int] = None) -> List[tuple[Datagram, bytes]]:
    """
    Read entire XTC file into memory.
    
    Args:
        filename: Path to XTC file
        max_events: Maximum number of events to read (None for all)
        
    Returns:
        List of (datagram, payload) tuples
    """
    events = []
    
    with XTCReader(filename) as reader:
        for i, (dgram, payload) in enumerate(reader):
            if max_events is not None and i >= max_events:
                break
            events.append((dgram, payload))
    
    return events


def get_xtc_info(filename: str, max_events: int = 10) -> dict:
    """
    Get summary information about an XTC file.
    
    Args:
        filename: Path to XTC file
        max_events: Number of events to analyze
        
    Returns:
        Dictionary with file statistics
    """
    info = {
        'filename': filename,
        'file_size': os.path.getsize(filename),
        'events_analyzed': 0,
        'type_counts': {},
        'damage_counts': {},
        'transition_counts': {}
    }
    
    with XTCReader(filename) as reader:
        for i, (dgram, payload) in enumerate(reader):
            if i >= max_events:
                break
                
            info['events_analyzed'] += 1
            
            # Count damage flags
            if dgram.xtc.damage.flags:
                damage_key = f"0x{dgram.xtc.damage.flags:06x}"
                info['damage_counts'][damage_key] = info['damage_counts'].get(damage_key, 0) + 1
            
            # Analyze XTC tree for type counts
            tree = walk_xtc_tree(payload, max_level=3)
            for level, xtc, data in tree:
                type_name = getattr(xtc.contains.type_id, 'name', f"Type_{xtc.contains.type_id}")
                info['type_counts'][type_name] = info['type_counts'].get(type_name, 0) + 1
    
    return info