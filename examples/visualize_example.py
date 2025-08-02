#!/usr/bin/env python3
"""
Example: Visualizing Detector Images

This example demonstrates how to use the visualization script with data
extracted by the xtc1reader CLI.

The workflow is:
1. Extract detector images using xtc1reader CLI
2. Visualize the extracted images using the visualization script
"""

import os
import subprocess
import sys


def run_extraction_example():
    """Example of extracting detector data using CLI."""
    
    # Example XTC file (adjust path as needed)
    xtc_file = "/sdf/data/lcls/ds/mfx/mfx100903824/xtc/e105-r0006-s00-c00.xtc"
    output_dir = "./extracted_images"
    
    print("=== Step 1: Extract Detector Images ===")
    print(f"Extracting from: {xtc_file}")
    print(f"Output directory: {output_dir}")
    
    # Run extraction command
    cmd = [
        "python", "-m", "xtc1reader.cli", "extract",
        xtc_file,
        "--output-dir", output_dir,
        "--detector", "epix10ka2m",
        "--max-events", "3"
    ]
    
    print("Running command:")
    print(" ".join(cmd))
    print()
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("✓ Extraction completed successfully!")
            print("Output:")
            print(result.stdout)
        else:
            print("✗ Extraction failed!")
            print("Error:", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("✗ Extraction timed out")
        return False
    except Exception as e:
        print(f"✗ Error running extraction: {e}")
        return False
    
    return True


def run_visualization_examples(output_dir="./extracted_images"):
    """Example of visualizing extracted images."""
    
    print("\n=== Step 2: Visualize Extracted Images ===")
    
    if not os.path.exists(output_dir):
        print(f"Output directory {output_dir} doesn't exist. Run extraction first.")
        return False
    
    # List available files
    import glob
    npy_files = glob.glob(os.path.join(output_dir, "*.npy"))
    if not npy_files:
        print("No .npy files found in output directory")
        return False
    
    print(f"Found {len(npy_files)} image files:")
    for f in npy_files[:5]:  # Show first 5
        print(f"  {os.path.basename(f)}")
    if len(npy_files) > 5:
        print(f"  ... and {len(npy_files) - 5} more")
    
    visualization_script = "../visualize_detector_images.py"
    
    # Example 1: Single image with default scaling (mean + 4*std)
    print("\n--- Example 1: Single Image (default scaling) ---")
    cmd1 = ["python", visualization_script, output_dir, "--mode", "single"]
    print("Command:", " ".join(cmd1))
    
    # Example 2: Comparison mode (raw, simple, psana assembly)
    print("\n--- Example 2: Assembly Comparison ---")
    cmd2 = ["python", visualization_script, output_dir, "--mode", "comparison"]
    print("Command:", " ".join(cmd2))
    
    # Example 3: Multi-event view
    print("\n--- Example 3: Multi-Event Grid ---")
    cmd3 = ["python", visualization_script, output_dir, "--mode", "multi", "--max-events", "6"]
    print("Command:", " ".join(cmd3))
    
    # Example 4: Custom scaling with different colormap
    print("\n--- Example 4: Custom Scaling ---")
    cmd4 = ["python", visualization_script, output_dir, "--scaling", "percentile", "--colormap", "plasma"]
    print("Command:", " ".join(cmd4))
    
    # Example 5: Save to file
    print("\n--- Example 5: Save Plot ---")
    cmd5 = ["python", visualization_script, output_dir, "--mode", "comparison", "--save", "detector_comparison.png"]
    print("Command:", " ".join(cmd5))
    
    print("\nTo run any of these examples, copy and paste the commands above.")
    print("The visualization script will open matplotlib windows (unless --save is used).")
    
    return True


def main():
    """Main example function."""
    
    print("Detector Image Visualization Example")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("../visualize_detector_images.py"):
        print("Error: Run this example from the examples/ directory")
        print("The visualization script should be in the parent directory")
        return 1
    
    print("This example demonstrates the two-step workflow:")
    print("1. Extract detector images using xtc1reader CLI")
    print("2. Visualize extracted images using the visualization script")
    print()
    
    # Ask user what they want to do
    print("Options:")
    print("  1. Run full example (extract + visualize)")
    print("  2. Show visualization examples only (if you already have extracted data)")
    print("  3. Show example commands only")
    
    try:
        choice = input("\nEnter choice (1-3): ").strip()
    except KeyboardInterrupt:
        print("\nExiting...")
        return 0
    
    if choice == "1":
        # Run extraction
        success = run_extraction_example()
        if success:
            run_visualization_examples()
        else:
            print("Extraction failed. Cannot proceed to visualization.")
            return 1
            
    elif choice == "2":
        # Just show visualization examples
        run_visualization_examples()
        
    elif choice == "3":
        # Show commands only
        print("\n=== Extraction Command ===")
        print("python -m xtc1reader.cli extract /path/to/data.xtc --output-dir ./images --detector epix10ka2m --max-events 5")
        
        print("\n=== Visualization Commands ===")
        print("python visualize_detector_images.py ./images                                    # Single image")
        print("python visualize_detector_images.py ./images --mode comparison                  # Compare assemblies")
        print("python visualize_detector_images.py ./images --mode multi                       # Multi-event grid")
        print("python visualize_detector_images.py ./images --scaling percentile --colormap hot # Custom scaling")
        print("python visualize_detector_images.py ./images --save output.png                  # Save to file")
        
    else:
        print("Invalid choice")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())