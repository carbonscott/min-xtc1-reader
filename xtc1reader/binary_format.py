"""
Binary format definitions and parsing for XTC files.

Based on analysis of LCLS1 pdsdata/xtc source code:
- Dgram: Sequence(16) + Env(4) + Xtc(16) = 36 bytes total header
- XTC: Damage(4) + Src(8) + TypeId(4) + extent(4) = 16 bytes  
- All values are little-endian
"""

import struct
from typing import NamedTuple, Optional
from enum import IntEnum


class TransitionId(IntEnum):
    """XTC transition types"""
    Unknown = 0
    Reset = 1
    Map = 2
    Unmap = 3
    Configure = 4
    Unconfigure = 5
    BeginRun = 6
    EndRun = 7
    BeginCalibCycle = 8
    EndCalibCycle = 9
    Enable = 10
    Disable = 11
    L1Accept = 12


class TypeId(IntEnum):
    """XTC data type identifiers - subset of most common types"""
    Any = 0
    Id_Xtc = 1          # Generic hierarchical container
    Id_Frame = 2        # Raw image frame
    Id_AcqWaveform = 3
    Id_AcqConfig = 4
    Id_TwoDGaussian = 5
    Id_Opal1kConfig = 6
    Id_FrameFexConfig = 7
    Id_EvrConfig = 8
    Id_TM6740Config = 9
    Id_ControlConfig = 10
    Id_pnCCDframe = 11
    Id_pnCCDconfig = 12
    Id_Epics = 13
    Id_FEEGasDetEnergy = 14
    Id_EBeam = 15
    Id_PhaseCavity = 16
    Id_PrincetonFrame = 17
    Id_PrincetonConfig = 18
    Id_EvrData = 19
    Id_FrameFccdConfig = 20
    Id_FccdConfig = 21
    Id_IpimbData = 22
    Id_IpimbConfig = 23
    Id_EncoderData = 24
    Id_EncoderConfig = 25
    Id_EvrIOConfig = 26
    Id_PrincetonInfo = 27
    Id_CspadElement = 28     # CSPad detector data
    Id_CspadConfig = 29      # CSPad configuration
    # Add more as needed...


class DamageFlags(IntEnum):
    """Damage bits indicating data quality issues"""
    DroppedContribution = 1
    Uninitialized = 11
    OutOfOrder = 12
    OutOfSynch = 13
    UserDefined = 14
    IncompleteContribution = 15
    ContainsIncomplete = 16


class ClockTime(NamedTuple):
    """8-byte timestamp: seconds + nanoseconds"""
    seconds: int        # uint32_t
    nanoseconds: int    # uint32_t
    
    def as_double(self) -> float:
        """Convert to floating point seconds"""
        return self.seconds + self.nanoseconds / 1e9


class TimeStamp(NamedTuple):
    """8-byte pulse timing information"""
    ticks: int       # 119MHz counter (24 bits)
    control: int     # Control bits (8 bits)
    fiducials: int   # 360Hz pulse ID (17 bits)
    vector: int      # Event distribution seed (15 bits)


class Sequence(NamedTuple):
    """16-byte sequence information: clock + timestamp"""
    clock: ClockTime
    stamp: TimeStamp


class Env(NamedTuple):
    """4-byte environment/configuration identifier"""
    value: int       # uint32_t


class Damage(NamedTuple):
    """4-byte damage flags"""
    value: int       # uint32_t
    
    @property
    def flags(self) -> int:
        """Lower 24 bits: standard damage flags"""
        return self.value & 0x00FFFFFF
    
    @property
    def user_bits(self) -> int:
        """Upper 8 bits: user-defined damage"""
        return (self.value >> 24) & 0xFF
    
    def has_damage(self, flag: DamageFlags) -> bool:
        """Check if specific damage flag is set"""
        return bool(self.flags & (1 << flag))


class Src(NamedTuple):
    """8-byte source identifier"""
    log: int         # uint32_t logical identifier
    phy: int         # uint32_t physical identifier
    
    @property 
    def level(self) -> int:
        """Source level from logical ID"""
        return (self.log >> 24) & 0xFF
    
    @property
    def process_id(self) -> int:
        """Process ID (for level=1 sources)"""
        return self.log & 0xFFFFFF
    
    @property
    def detector_type(self) -> int:
        """Detector type from physical ID"""
        return (self.phy >> 24) & 0xFF
    
    @property 
    def detector_id(self) -> int:
        """Detector ID from physical ID"""
        return (self.phy >> 16) & 0xFF
    
    @property
    def device_type(self) -> int:
        """Device type from physical ID"""
        return (self.phy >> 8) & 0xFF
    
    @property
    def device_id(self) -> int:
        """Device ID from physical ID"""
        return self.phy & 0xFF


class TypeIdInfo(NamedTuple):
    """4-byte type identifier"""
    value: int       # uint32_t
    
    @property
    def type_id(self) -> int:
        """Type ID (bits 0-15)"""
        return self.value & 0xFFFF
    
    @property
    def version(self) -> int:
        """Version number (bits 16-30)"""
        return (self.value >> 16) & 0x7FFF
    
    @property
    def compressed(self) -> bool:
        """Compression flag (bit 31)"""
        return bool(self.value & 0x80000000)


class XTCContainer(NamedTuple):
    """16-byte XTC container header"""
    damage: Damage
    src: Src  
    contains: TypeIdInfo
    extent: int      # uint32_t total size including header
    
    @property
    def payload_size(self) -> int:
        """Size of payload data (extent - header size)"""
        return self.extent - 20  # XTC header is 20 bytes


class Datagram(NamedTuple):
    """Complete datagram: 24-byte header + XTC payload"""
    seq: Sequence
    env: Env
    xtc: XTCContainer


# Binary parsing functions using little-endian format

def parse_datagram_header(data: bytes) -> Datagram:
    """
    Parse 24-byte datagram header from binary data.
    
    Format: Sequence(16) + Env(4) + partial XTC(4 damage bytes)
    Note: Remaining 12 bytes of XTC header are in payload
    """
    if len(data) < 24:
        raise ValueError(f"Datagram header too short: {len(data)} < 24 bytes")
    
    # Parse Sequence (16 bytes)
    clock_ns, clock_sec, stamp_low, stamp_high = struct.unpack('<4I', data[0:16])
    
    # Extract timestamp fields  
    ticks = stamp_low & 0xFFFFFF
    control = (stamp_low >> 24) & 0xFF
    fiducials = stamp_high & 0x1FFFF
    vector = (stamp_high >> 17) & 0x7FFF
    
    clock = ClockTime(clock_sec, clock_ns)
    stamp = TimeStamp(ticks, control, fiducials, vector)
    seq = Sequence(clock, stamp)
    
    # Parse Env (4 bytes)
    env_val = struct.unpack('<I', data[16:20])[0]
    env = Env(env_val)
    
    # Parse first 4 bytes of XTC (damage field)
    damage_val = struct.unpack('<I', data[20:24])[0]
    damage = Damage(damage_val)
    
    # XTC container is incomplete - need remaining 12 bytes from payload
    # Return partial datagram for now
    return Datagram(seq, env, XTCContainer(damage, Src(0, 0), TypeIdInfo(0), 0))


def parse_xtc_header(data: bytes, offset: int = 0) -> XTCContainer:
    """
    Parse 20-byte XTC container header from binary data.
    
    Format: Damage(4) + Src_log(4) + Src_phy(4) + TypeId(4) + extent(4) = 20 bytes
    """
    if len(data) < offset + 20:
        raise ValueError(f"XTC header too short at offset {offset}")
    
    # Unpack all 20 bytes: damage + src_log + src_phy + typeid + extent
    damage_val, src_log, src_phy, typeid_val, extent = struct.unpack(
        '<5I', data[offset:offset+20]
    )
    
    damage = Damage(damage_val)
    src = Src(src_log, src_phy)
    contains = TypeIdInfo(typeid_val)
    
    return XTCContainer(damage, src, contains, extent)


def complete_datagram_with_xtc(partial_dgram: Datagram, xtc_data: bytes) -> Datagram:
    """
    Complete a partial datagram by parsing the full XTC header from payload.
    """
    if len(xtc_data) < 16:
        raise ValueError("XTC data too short for remaining header")
    
    # Parse remaining XTC fields (src_log + src_phy + typeid + extent)
    src_log, src_phy, typeid_val, extent = struct.unpack('<4I', xtc_data[0:16])
    
    src = Src(src_log, src_phy)
    contains = TypeIdInfo(typeid_val)
    
    # Create complete XTC container  
    xtc = XTCContainer(partial_dgram.xtc.damage, src, contains, extent)
    
    return Datagram(partial_dgram.seq, partial_dgram.env, xtc)


def parse_xtc_payload(data: bytes, offset: int = 0) -> tuple[list[XTCContainer], int]:
    """
    Parse XTC containers from payload data recursively.
    
    Returns: (list of XTC containers, bytes consumed)
    """
    containers = []
    pos = offset
    
    while pos + 16 <= len(data):
        xtc = parse_xtc_header(data, pos)
        containers.append(xtc)
        
        # Move to next XTC (current header + payload)
        pos += xtc.extent
        
        # Stop if we've consumed all data
        if pos >= len(data):
            break
    
    return containers, pos - offset


def type_id_name(type_id: int) -> str:
    """Get human-readable name for type ID"""
    try:
        return TypeId(type_id).name
    except ValueError:
        return f"Unknown_{type_id}"


def transition_name(transition_id: int) -> str:
    """Get human-readable name for transition ID"""
    try:
        return TransitionId(transition_id).name
    except ValueError:
        return f"Unknown_{transition_id}"