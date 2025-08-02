#!/usr/bin/env python3
"""
Detector Image Visualization Script

Uses matplotlib to visualize detector images extracted by xtc1reader CLI.
Supports multiple visualization modes with smart intensity scaling.

Usage:
    python visualize_detector_images.py /path/to/extracted/images/
    python visualize_detector_images.py /path/to/images/ --mode comparison
    python visualize_detector_images.py /path/to/images/ --scaling custom --vmin 100 --vmax 2000
"""

import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import glob
from pathlib import Path
from typing import Optional, Tuple, List


def smart_scaling(image: np.ndarray, method: str = 'mean_std') -> Tuple[float, float]:
    """
    Calculate smart intensity scaling for detector images.
    
    Args:
        image: 2D detector image array
        method: Scaling method ('mean_std', 'percentile', 'minmax')
        
    Returns:
        (vmin, vmax) intensity range for display
    """
    # Mask out zero/invalid pixels
    valid_pixels = image[image > 0]
    
    if len(valid_pixels) == 0:
        return 0, 1
    
    if method == 'mean_std':
        # User's requested scaling: min=mean, max=mean+4*std
        mean_val = np.mean(valid_pixels)
        std_val = np.std(valid_pixels)
        vmin = mean_val
        vmax = mean_val + 4 * std_val
        
    elif method == 'percentile':
        # Robust percentile-based scaling
        vmin = np.percentile(valid_pixels, 1)
        vmax = np.percentile(valid_pixels, 99)
        
    elif method == 'minmax':
        # Simple min/max scaling
        vmin = np.min(valid_pixels)
        vmax = np.max(valid_pixels)
        
    else:
        raise ValueError(f"Unknown scaling method: {method}")
    
    return float(vmin), float(vmax)


def find_image_files(directory: str, pattern: str = "*.npy") -> List[str]:
    """Find all .npy image files in directory matching pattern."""
    search_path = os.path.join(directory, pattern)
    files = glob.glob(search_path)
    return sorted(files)


def load_and_validate_image(filepath: str) -> Optional[np.ndarray]:
    """Load image file and validate/convert to 2D array."""
    try:
        image = np.load(filepath)
        
        if image.ndim == 2:
            return image
        elif image.ndim == 3:
            # Handle raw detector frames (e.g., 16x352x384) - sum or take first panel
            if 'raw' in filepath.lower():
                # For raw frames, create a mosaic view or sum all panels
                print(f"Converting 3D raw frames {image.shape} to 2D mosaic")
                # Simple 4x4 grid of panels
                if image.shape[0] == 16:  # Epix10ka2M has 16 panels
                    panels = []
                    for i in range(4):
                        row_panels = []
                        for j in range(4):
                            panel_idx = i * 4 + j
                            row_panels.append(image[panel_idx])
                        panels.append(np.hstack(row_panels))
                    return np.vstack(panels)
                else:
                    # Fallback: sum all frames
                    return np.sum(image, axis=0)
            else:
                print(f"Warning: {filepath} has unexpected 3D shape: {image.shape}")
                return np.sum(image, axis=0)
        else:
            print(f"Warning: {filepath} has unsupported shape: {image.shape}")
            return None
            
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def plot_single_image(image: np.ndarray, title: str, scaling: str = 'mean_std', 
                     vmin: Optional[float] = None, vmax: Optional[float] = None,
                     colormap: str = 'viridis', use_log: bool = False):
    """Plot a single detector image with specified scaling."""
    
    # Calculate intensity range
    if vmin is None or vmax is None:
        calc_vmin, calc_vmax = smart_scaling(image, scaling)
        if vmin is None:
            vmin = calc_vmin
        if vmax is None:
            vmax = calc_vmax
    
    # Create figure
    plt.figure(figsize=(10, 8))
    
    # Plot image
    norm = LogNorm(vmin=max(vmin, 1), vmax=vmax) if use_log else None
    im = plt.imshow(image, cmap=colormap, vmin=vmin, vmax=vmax, norm=norm, 
                   origin='upper', interpolation='nearest')
    
    # Add colorbar
    cbar = plt.colorbar(im, shrink=0.8)
    cbar.set_label('Intensity (ADU)', rotation=270, labelpad=15)
    
    # Add labels and title
    plt.title(title, fontsize=14, pad=20)
    plt.xlabel('X pixels')
    plt.ylabel('Y pixels')
    
    # Add statistics text
    valid_pixels = image[image > 0]
    if len(valid_pixels) > 0:
        stats_text = f'Shape: {image.shape}\n'
        stats_text += f'Valid pixels: {len(valid_pixels):,}\n'
        stats_text += f'Mean: {np.mean(valid_pixels):.1f}\n'
        stats_text += f'Std: {np.std(valid_pixels):.1f}\n'
        stats_text += f'Range: [{vmin:.1f}, {vmax:.1f}]'
        
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                fontsize=10, verticalalignment='top', 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()


def plot_comparison(images: List[np.ndarray], titles: List[str], 
                   scaling: str = 'mean_std', colormap: str = 'viridis'):
    """Plot multiple images side by side for comparison."""
    
    n_images = len(images)
    if n_images == 0:
        return
    
    # Calculate common intensity range for fair comparison
    all_valid_pixels = []
    for img in images:
        valid = img[img > 0]
        if len(valid) > 0:
            all_valid_pixels.extend(valid)
    
    if len(all_valid_pixels) > 0:
        combined_image = np.array(all_valid_pixels)
        vmin, vmax = smart_scaling(combined_image.reshape(-1, 1), scaling)
    else:
        vmin, vmax = 0, 1
    
    # Create subplot layout
    cols = min(3, n_images)
    rows = (n_images + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows))
    if n_images == 1:
        axes = [axes]
    elif rows == 1 and n_images > 1:
        axes = axes.reshape(1, -1)
    elif rows > 1:
        axes = axes.flatten()
    
    for i, (image, title) in enumerate(zip(images, titles)):
        if n_images == 1:
            ax = axes[0] if isinstance(axes, list) else axes
        else:
            ax = axes[i]
        
        # Plot image
        im = ax.imshow(image, cmap=colormap, vmin=vmin, vmax=vmax, 
                      origin='upper', interpolation='nearest')
        
        # Add title and labels
        ax.set_title(title, fontsize=12)
        ax.set_xlabel('X pixels')
        ax.set_ylabel('Y pixels')
        
        # Add statistics
        valid_pixels = image[image > 0]
        if len(valid_pixels) > 0:
            stats = f'{image.shape[0]}×{image.shape[1]}\n{len(valid_pixels):,} pixels'
            ax.text(0.02, 0.98, stats, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    # Hide unused subplots
    if n_images > 1:
        for i in range(n_images, len(axes)):
            axes[i].set_visible(False)
    
    # Add shared colorbar
    plt.subplots_adjust(right=0.85)
    cbar_ax = fig.add_axes([0.87, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label('Intensity (ADU)', rotation=270, labelpad=15)
    
    plt.suptitle(f'Detector Image Comparison (scaling: {scaling})', fontsize=14)
    plt.tight_layout()


def plot_multi_event(image_files: List[str], max_events: int = 9,
                    scaling: str = 'mean_std', colormap: str = 'viridis'):
    """Plot multiple events in a grid layout."""
    
    # Load up to max_events images
    images = []
    titles = []
    
    for i, filepath in enumerate(image_files[:max_events]):
        image = load_and_validate_image(filepath)
        if image is not None:
            images.append(image)
            filename = os.path.basename(filepath)
            # Extract event number from filename
            event_num = filename.split('_')[1] if '_' in filename else str(i)
            titles.append(f'Event {event_num}')
    
    if not images:
        print("No valid images found!")
        return
    
    # Calculate grid layout
    n_images = len(images)
    cols = int(np.ceil(np.sqrt(n_images)))
    rows = int(np.ceil(n_images / cols))
    
    fig, axes = plt.subplots(rows, cols, figsize=(4*cols, 3*rows))
    if n_images == 1:
        axes = [axes]
    elif rows == 1:
        axes = axes.reshape(1, -1)
    
    # Calculate common intensity range
    all_pixels = np.concatenate([img[img > 0] for img in images if len(img[img > 0]) > 0])
    if len(all_pixels) > 0:
        vmin, vmax = smart_scaling(all_pixels.reshape(-1, 1), scaling)
    else:
        vmin, vmax = 0, 1
    
    for i, (image, title) in enumerate(zip(images, titles)):
        row = i // cols
        col = i % cols
        ax = axes[row, col] if rows > 1 else axes[col]
        
        # Plot image
        im = ax.imshow(image, cmap=colormap, vmin=vmin, vmax=vmax, 
                      origin='upper', interpolation='nearest')
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add shape info
        ax.text(0.05, 0.95, f'{image.shape[0]}×{image.shape[1]}', 
               transform=ax.transAxes, fontsize=8, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
    
    # Hide unused subplots
    for i in range(n_images, rows * cols):
        row = i // cols
        col = i % cols
        ax = axes[row, col] if rows > 1 else axes[col]
        ax.set_visible(False)
    
    # Add shared colorbar
    fig.subplots_adjust(right=0.85)
    cbar_ax = fig.add_axes([0.87, 0.15, 0.03, 0.7])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label('Intensity (ADU)', rotation=270, labelpad=15)
    
    plt.suptitle(f'Multi-Event View ({len(images)} events)', fontsize=14)
    plt.tight_layout()


def plot_panel_view(image: np.ndarray, title: str, panels_shape: Tuple[int, int] = (4, 4)):
    """Plot individual panels of a detector image (for debugging)."""
    
    rows, cols = image.shape
    panel_rows = rows // panels_shape[0]
    panel_cols = cols // panels_shape[1]
    
    fig, axes = plt.subplots(panels_shape[0], panels_shape[1], 
                            figsize=(2*panels_shape[1], 2*panels_shape[0]))
    
    for i in range(panels_shape[0]):
        for j in range(panels_shape[1]):
            ax = axes[i, j]
            
            # Extract panel
            start_row = i * panel_rows
            end_row = (i + 1) * panel_rows
            start_col = j * panel_cols  
            end_col = (j + 1) * panel_cols
            
            panel = image[start_row:end_row, start_col:end_col]
            
            # Plot panel
            im = ax.imshow(panel, cmap='viridis', origin='upper')
            ax.set_title(f'Panel {i},{j}', fontsize=8)
            ax.set_xticks([])
            ax.set_yticks([])
    
    plt.suptitle(f'{title} - Panel View', fontsize=12)
    plt.tight_layout()


def main():
    parser = argparse.ArgumentParser(
        description="Visualize detector images extracted by xtc1reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python visualize_detector_images.py ./extracted_images/
  python visualize_detector_images.py ./images/ --mode comparison
  python visualize_detector_images.py ./images/ --mode multi
  python visualize_detector_images.py ./images/ --scaling percentile --colormap plasma
  python visualize_detector_images.py ./images/ --scaling custom --vmin 100 --vmax 2000
        """
    )
    
    parser.add_argument('directory', help='Directory containing extracted .npy image files')
    parser.add_argument('--mode', choices=['single', 'comparison', 'multi', 'panels'], 
                       default='single', help='Visualization mode (default: single)')
    parser.add_argument('--scaling', choices=['mean_std', 'percentile', 'minmax', 'custom'],
                       default='mean_std', help='Intensity scaling method (default: mean_std)')
    parser.add_argument('--vmin', type=float, help='Minimum intensity (for custom scaling)')
    parser.add_argument('--vmax', type=float, help='Maximum intensity (for custom scaling)')
    parser.add_argument('--colormap', default='viridis', 
                       help='Matplotlib colormap name (default: viridis)')
    parser.add_argument('--pattern', default='*psana*.npy',
                       help='File pattern to search for (default: *psana*.npy)')
    parser.add_argument('--max-events', type=int, default=9,
                       help='Maximum events to show in multi mode (default: 9)')
    parser.add_argument('--log-scale', action='store_true',
                       help='Use logarithmic color scale')
    parser.add_argument('--save', help='Save plot to file instead of displaying')
    parser.add_argument('--dpi', type=int, default=150, help='DPI for saved plots')
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        return 1
    
    # Find image files
    image_files = find_image_files(args.directory, args.pattern)
    if not image_files:
        print(f"No image files found matching pattern '{args.pattern}' in {args.directory}")
        print("Available files:")
        all_files = find_image_files(args.directory, "*.npy")
        for f in all_files[:10]:  # Show first 10
            print(f"  {os.path.basename(f)}")
        if len(all_files) > 10:
            print(f"  ... and {len(all_files) - 10} more")
        return 1
    
    print(f"Found {len(image_files)} image files matching pattern '{args.pattern}'")
    
    # Validate custom scaling parameters
    if args.scaling == 'custom':
        if args.vmin is None or args.vmax is None:
            print("Error: --vmin and --vmax required for custom scaling")
            return 1
    
    # Execute visualization based on mode
    try:
        if args.mode == 'single':
            # Load first image
            image = load_and_validate_image(image_files[0])
            if image is None:
                return 1
            
            title = f"Detector Image: {os.path.basename(image_files[0])}"
            plot_single_image(image, title, args.scaling, args.vmin, args.vmax, 
                            args.colormap, args.log_scale)
            
        elif args.mode == 'comparison':
            # Load multiple assembly types for comparison
            base_pattern = image_files[0].replace('_psana.npy', '')
            comparison_files = []
            comparison_titles = []
            
            # Look for different assembly types
            for suffix, label in [('_raw.npy', 'Raw Frames'), 
                                ('_simple.npy', 'Simple Assembly'),
                                ('_psana.npy', 'Psana Assembly')]:
                test_file = base_pattern + suffix
                if os.path.exists(test_file):
                    comparison_files.append(test_file)
                    comparison_titles.append(label)
            
            if not comparison_files:
                print("No comparison files found. Looking for any images...")
                comparison_files = image_files[:3]
                comparison_titles = [os.path.basename(f) for f in comparison_files]
            
            # Load images
            images = []
            valid_titles = []
            for filepath, title in zip(comparison_files, comparison_titles):
                img = load_and_validate_image(filepath)
                if img is not None:
                    images.append(img)
                    valid_titles.append(title)
            
            if images:
                plot_comparison(images, valid_titles, args.scaling, args.colormap)
            else:
                print("No valid comparison images found")
                return 1
                
        elif args.mode == 'multi':
            plot_multi_event(image_files, args.max_events, args.scaling, args.colormap)
            
        elif args.mode == 'panels':
            # Load first image for panel view
            image = load_and_validate_image(image_files[0])
            if image is None:
                return 1
                
            title = os.path.basename(image_files[0])
            plot_panel_view(image, title)
        
        # Save or show plot
        if args.save:
            plt.savefig(args.save, dpi=args.dpi, bbox_inches='tight')
            print(f"Plot saved to: {args.save}")
        else:
            plt.show()
        
    except KeyboardInterrupt:
        print("\nVisualization interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during visualization: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())