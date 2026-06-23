#!/usr/bin/env python3
"""
Cleanup script for the BDA Optimizer.
Removes all generated files from previous runs.
"""
import os
import glob
import shutil

def cleanup():
    """
    Clean up all generated files from previous runs.
    """
    print("🧹 Cleaning up generated files...")
    
    # Files to remove from the main directory
    patterns = [
        "input_sequential_*.json",  # Old input files
        "strategy_report_*.csv"     # Old strategy reports
    ]
    
    # Redundant directories to remove from project folder
    redundant_dirs = [
        "bda_output",
        "html_output",
        "inputs",
        "merged_df_output",
        "reports",
        "schemas",
        "similarity_output",
        "__pycache__"  # Python bytecode cache
    ]
    
    # Legacy files to remove from the src directory
    src_patterns = [
        "src/schema_sequential_*.json"  # Old schema files
    ]
    
    # Create output directory if it doesn't exist
    if not os.path.exists("output"):
        try:
            os.makedirs("output", exist_ok=True)
            print(f"  ✓ Created output directory")
        except Exception as e:
            print(f"  ✗ Failed to create output directory: {e}")
    
    # Run-specific directories (with run_TIMESTAMP subdirectories)
    # These directories contain subdirectories for each run (e.g., run_20240620_123456)
    # Now moved to the output directory
    run_dirs_to_clean = [
        "output/schemas",    # Contains schema files for each run
        "output/reports",    # Contains report files for each run
        "output/inputs"      # Contains input files for each run
    ]
    
    # Directories to clean completely (remove all files but keep the directory)
    dirs_to_clean_completely = [
        "output/blueprints"  # Contains downloaded blueprint files
    ]
    
    # Output directories (store files but don't have run_TIMESTAMP subdirectories)
    # These directories contain output files that are not organized by run
    # Now moved to the output directory, except for logs
    output_dirs_to_clean = [
        "output/bda_output/sequential",           # Raw BDA output files
        "output/html_output",                     # HTML visualization files
        "output/similarity_output/sequential",    # Similarity score files
        "output/merged_df_output/sequential",     # Merged dataframe files
        "logs"                                    # Log files (stays at root level)
    ]
    
    # Step 1: Remove legacy files from the main directory
    for pattern in patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed legacy file {file_path}")
            except Exception as e:
                print(f"  ✗ Failed to remove {file_path}: {e}")
    
    # Step 2: Remove legacy files from the src directory
    for pattern in src_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"  ✓ Removed legacy file {file_path}")
            except Exception as e:
                print(f"  ✗ Failed to remove {file_path}: {e}")
    
    # Step 2.5: Remove redundant directories from project folder
    for dir_name in redundant_dirs:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  ✓ Removed redundant directory {dir_name}/")
            except Exception as e:
                print(f"  ✗ Failed to remove {dir_name}/: {e}")
    
    # Step 3: Clean run-specific directories (remove run_* subdirectories)
    for dir_path in run_dirs_to_clean:
        if os.path.exists(dir_path):
            try:
                # Remove all run directories
                for run_dir in glob.glob(f"{dir_path}/run_*"):
                    shutil.rmtree(run_dir)
                    print(f"  ✓ Removed {run_dir}")
            except Exception as e:
                print(f"  ✗ Failed to clean {dir_path}: {e}")
        else:
            # Create the directory if it doesn't exist
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  ✓ Created {dir_path}")
            except Exception as e:
                print(f"  ✗ Failed to create {dir_path}: {e}")
    
    # Step 4: Clean directories completely (remove all files but keep the directory)
    for dir_path in dirs_to_clean_completely:
        if os.path.exists(dir_path):
            try:
                # Remove all files in the directory
                for file_path in glob.glob(f"{dir_path}/*"):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    else:
                        shutil.rmtree(file_path)
                print(f"  ✓ Cleaned {dir_path} completely")
            except Exception as e:
                print(f"  ✗ Failed to clean {dir_path}: {e}")
        else:
            # Create the directory if it doesn't exist
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  ✓ Created {dir_path}")
            except Exception as e:
                print(f"  ✗ Failed to create {dir_path}: {e}")
    
    # Step 5: Clean output directories (remove all files but keep the directory)
    for dir_path in output_dirs_to_clean:
        if os.path.exists(dir_path):
            try:
                # Remove all files in the directory
                for file_path in glob.glob(f"{dir_path}/*"):
                    os.remove(file_path)
                print(f"  ✓ Cleaned {dir_path}")
            except Exception as e:
                print(f"  ✗ Failed to clean {dir_path}: {e}")
        else:
            # Create the directory if it doesn't exist
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  ✓ Created {dir_path}")
            except Exception as e:
                print(f"  ✗ Failed to create {dir_path}: {e}")
    
    print("✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup()
