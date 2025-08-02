#!/usr/bin/env python3
"""
Detector Discovery Module for Psana Compatibility

This module provides functionality to discover and resolve detector configurations
in a way that's compatible with the LCLS/psana ecosystem, bridging the gap between
direct XTC parsing and psana's detector data management system.
"""

import os
import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple
from .binary_format import TypeId


class DetectorInfo(NamedTuple):
    """Information about a detector discovered in the LCLS data system"""
    experiment: str
    detector_name: str              # User-friendly name (e.g., 'epix10k2M')
    detector_id: str                # Full LCLS detector ID (e.g., 'MfxEndstation.0:Epix10ka2M.0')
    detector_type: str              # Detector type (e.g., 'Epix10ka2M')
    calib_dir: str                  # Path to calibration directory
    geometry_files: List[str]       # Available geometry files
    typeid_mappings: Dict[int, str] # TypeId mappings for this detector/experiment


class LCLSEnvironment:
    """Manages LCLS environment and data location discovery"""
    
    def __init__(self):
        self.data_root = self._get_data_root()
        self._detector_cache = {}
    
    def _get_data_root(self) -> str:
        """Get LCLS data root from environment or use default"""
        data_root = os.environ.get('SIT_PSDM_DATA', '/sdf/data/lcls/ds')
        if not os.path.exists(data_root):
            raise RuntimeError(f"LCLS data directory not found: {data_root}")
        return data_root
    
    def get_experiment_path(self, experiment: str) -> str:
        """Get full path to experiment directory"""
        # LCLS experiments follow pattern: instrument/experiment
        # Extract instrument from experiment name (e.g., 'mfx100903824' -> 'mfx')
        instrument = ''.join(c for c in experiment if c.isalpha())
        exp_path = os.path.join(self.data_root, instrument, experiment)
        
        if not os.path.exists(exp_path):
            raise RuntimeError(f"Experiment directory not found: {exp_path}")
        
        return exp_path
    
    def discover_detectors(self, experiment: str) -> List[DetectorInfo]:
        """Discover all detectors available for an experiment"""
        
        if experiment in self._detector_cache:
            return self._detector_cache[experiment]
        
        exp_path = self.get_experiment_path(experiment)
        calib_path = os.path.join(exp_path, 'calib')
        
        if not os.path.exists(calib_path):
            print(f"Warning: No calibration directory found at {calib_path}")
            return []
        
        detectors = []
        
        # Scan calibration directory for detector types
        for detector_calib_dir in glob.glob(os.path.join(calib_path, '*')):
            if not os.path.isdir(detector_calib_dir):
                continue
                
            detector_calib_name = os.path.basename(detector_calib_dir)
            
            # Parse detector calibration directory name (e.g., 'Epix10ka2M::CalibV1')
            if '::' not in detector_calib_name:
                continue
                
            detector_type = detector_calib_name.split('::')[0]
            
            # Find detector instances within this calibration directory
            for detector_instance_dir in glob.glob(os.path.join(detector_calib_dir, '*')):
                if not os.path.isdir(detector_instance_dir):
                    continue
                    
                detector_id = os.path.basename(detector_instance_dir)
                
                # Parse detector ID (e.g., 'MfxEndstation.0:Epix10ka2M.0')
                if ':' not in detector_id:
                    continue
                    
                # Create user-friendly detector name
                detector_name = self._create_detector_name(detector_type)
                
                # Find geometry files
                geometry_dir = os.path.join(detector_instance_dir, 'geometry')
                geometry_files = []
                if os.path.exists(geometry_dir):
                    geometry_files = glob.glob(os.path.join(geometry_dir, '*.geom'))
                
                # Get TypeId mappings (experiment/detector specific)
                typeid_mappings = self._discover_typeids(experiment, detector_type)
                
                detector_info = DetectorInfo(
                    experiment=experiment,
                    detector_name=detector_name,
                    detector_id=detector_id,
                    detector_type=detector_type,
                    calib_dir=detector_instance_dir,
                    geometry_files=geometry_files,
                    typeid_mappings=typeid_mappings
                )
                
                detectors.append(detector_info)
        
        self._detector_cache[experiment] = detectors
        return detectors
    
    def _create_detector_name(self, detector_type: str) -> str:
        """Create user-friendly detector name from detector type"""
        # Map detector types to psana-compatible names
        type_mappings = {
            'Epix10ka2M': 'epix10k2M',
            'CsPad': 'cspad',
            'pnCCD': 'pnccd',
            'Princeton': 'princeton',
            'Jungfrau': 'jungfrau'
        }
        return type_mappings.get(detector_type, detector_type.lower())
    
    def _discover_typeids(self, experiment: str, detector_type: str) -> Dict[int, str]:
        """Discover TypeId mappings for specific experiment/detector combinations"""
        
        # Known TypeId mappings discovered through investigation
        known_mappings = {
            # Standard LCLS TypeIds (from our implementation)
            ('*', 'Epix10ka2M'): {
                TypeId.Id_Epix10kaArray: 'Epix10ka2M_array',
                TypeId.Id_Epix10kaConfig: 'Epix10ka2M_config',
                TypeId.Id_Epix10ka2MConfig: 'Epix10ka2M_config_v2'
            },
            
            # Experiment-specific TypeIds (discovered from real data)
            ('mfx100903824', 'Epix10ka2M'): {
                6185: 'Epix10ka2M_config_experimental',
                6190: 'Epix10ka2M_config_v2_experimental', 
                6193: 'Epix10ka2M_array_experimental'
            }
        }
        
        # Try experiment-specific mapping first, then fallback to generic
        mappings = {}
        
        if (experiment, detector_type) in known_mappings:
            mappings.update(known_mappings[(experiment, detector_type)])
        
        if ('*', detector_type) in known_mappings:
            mappings.update(known_mappings[('*', detector_type)])
            
        return mappings
    
    def find_detector(self, experiment: str, detector_name: str) -> Optional[DetectorInfo]:
        """Find specific detector by name"""
        detectors = self.discover_detectors(experiment)
        
        for detector in detectors:
            if detector.detector_name.lower() == detector_name.lower():
                return detector
                
        return None
    
    def get_xtc_files(self, experiment: str, run: str) -> List[str]:
        """Get XTC files for a specific experiment and run"""
        exp_path = self.get_experiment_path(experiment)
        xtc_path = os.path.join(exp_path, 'xtc')
        
        if not os.path.exists(xtc_path):
            return []
        
        # Find XTC files matching the run pattern
        pattern = f"{experiment}-r{run:0>4s}-s*-c*.xtc"
        xtc_files = glob.glob(os.path.join(xtc_path, pattern))
        
        return sorted(xtc_files)


def create_detector_discovery() -> LCLSEnvironment:
    """Factory function to create detector discovery instance"""
    return LCLSEnvironment()


def resolve_detector_from_psana_style(exp: str, run: str, detector_name: str) -> Tuple[Optional[DetectorInfo], List[str]]:
    """
    Resolve detector information from psana-style parameters
    
    Args:
        exp: Experiment name (e.g., 'mfx100903824')
        run: Run number (e.g., '105')
        detector_name: Detector name (e.g., 'epix10k2M')
        
    Returns:
        Tuple of (DetectorInfo or None, list of XTC files)
    """
    
    env = create_detector_discovery()
    
    # Find detector
    detector_info = env.find_detector(exp, detector_name)
    
    # Get XTC files
    xtc_files = env.get_xtc_files(exp, run)
    
    return detector_info, xtc_files


# Example usage and testing functions
def print_detector_discovery_summary(experiment: str):
    """Print summary of discovered detectors for debugging"""
    
    print(f"Detector Discovery Summary for {experiment}")
    print("=" * 60)
    
    try:
        env = create_detector_discovery()
        detectors = env.discover_detectors(experiment)
        
        if not detectors:
            print("No detectors found!")
            return
            
        for detector in detectors:
            print(f"\nDetector: {detector.detector_name}")
            print(f"  ID: {detector.detector_id}")
            print(f"  Type: {detector.detector_type}")
            print(f"  Calib Dir: {detector.calib_dir}")
            print(f"  Geometry Files: {len(detector.geometry_files)}")
            print(f"  TypeId Mappings: {detector.typeid_mappings}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Test detector discovery
    print_detector_discovery_summary('mfx100903824')