import os
import shutil
import subprocess
import glob

def process_bag_files(source_folder, rs_convert_path):
    """
    Process all .bag files in the source folder:
    1. Create a dedicated folder for each .bag file
    2. Copy the original .bag file to the new folder
    3. Create subfolders for .ply and .png files
    4. Extract .ply and .png files using rs-convert.exe
    
    Args:
        source_folder (str): Path to the folder containing .bag files
        rs_convert_path (str): Path to rs-convert.exe
    """
    # Ensure the source folder path ends with a backslash
    if not source_folder.endswith('\\'):
        source_folder += '\\'
    
    # Get all .bag files in the source folder
    bag_files = glob.glob(source_folder + '*.bag')
    
    if not bag_files:
        print(f"No .bag files found in {source_folder}")
        return
    
    print(f"Found {len(bag_files)} .bag files to process")
    
    # Process each .bag file
    for bag_file in bag_files:
        bag_filename = os.path.basename(bag_file)
        item_name = os.path.splitext(bag_filename)[0]
        
        # Create a new folder for this item
        item_folder = os.path.join(source_folder, item_name)
        os.makedirs(item_folder, exist_ok=True)
        
        # Create subfolders for .ply and .png files
        ply_folder = os.path.join(item_folder, f"{item_name}_ply")
        png_folder = os.path.join(item_folder, f"{item_name}_png")
        os.makedirs(ply_folder, exist_ok=True)
        os.makedirs(png_folder, exist_ok=True)
        
        # Copy the original .bag file to the new folder
        item_bag_file = os.path.join(item_folder, bag_filename)
        print(f"Copying {bag_filename} to {item_folder}")
        shutil.copy2(bag_file, item_bag_file)
        
        # Extract .ply and .png files using rs-convert.exe
        print(f"Extracting .ply and .png files from {bag_filename}")
        
        # Create full paths for extraction
        ply_output_path = os.path.join(ply_folder, "ply")
        png_output_path = os.path.join(png_folder, "png")
        
        # Build the command to run rs-convert.exe
        command = [
            rs_convert_path,
            "-i", bag_file,
            "-l", ply_output_path,
            "-p", png_output_path
        ]
        
        try:
            # Execute the command
            subprocess.run(command, check=True)
            print(f"Successfully processed {bag_filename}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing {bag_filename}: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    # Update these paths to match your environment
    source_folder = r"F:\Robot Vision\training data"
    rs_convert_path = r"F:\Robot Vision\rs-convert\rs-convert.exe"
    
    process_bag_files(source_folder, rs_convert_path)
    print("Processing complete!")