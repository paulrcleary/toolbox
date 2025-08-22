import os
from PIL import Image

def convert_tiff_to_png(source_folder, destination_folder):
    """
    Converts all TIFF files in a source folder to PNG format and saves them
    to a destination folder.

    Args:
        source_folder (str): The path to the folder containing .tiff files.
        destination_folder (str): The path to the folder where .png files will be saved.
    """
    # Create the destination folder if it doesn't exist
    if not os.path.exists(destination_folder):
        print(f"Creating destination folder: {destination_folder}")
        os.makedirs(destination_folder)

    # Loop through all files in the source folder
    for filename in os.listdir(source_folder):
        # Check if the file is a TIFF file
        if filename.lower().endswith(('.tif', '.tiff')):
            try:
                # Construct the full file path
                tiff_path = os.path.join(source_folder, filename)
                
                # Open the TIFF image
                with Image.open(tiff_path) as img:
                    # Create the output filename by changing the extension to .png
                    base_filename = os.path.splitext(filename)[0]
                    png_filename = f"{base_filename}.png"
                    png_path = os.path.join(destination_folder, png_filename)
                    
                    # Save the image as a PNG file
                    print(f"Converting {filename} to {png_filename}...")
                    img.save(png_path, 'PNG')
                    
            except Exception as e:
                print(f"Could not convert {filename}. Reason: {e}")

    print("\nConversion complete!")

if __name__ == '__main__':
    # --- Configuration ---
    # IMPORTANT: Replace these paths with your actual folder paths.
    # Use '.' to represent the current directory where the script is running.
    
    # Folder containing your .tiff files
    input_folder = 'tiff_images' 
    
    # Folder where you want to save the converted .png files
    output_folder = 'png_images'
    # --- End of Configuration ---

    # --- Create a dummy folder and files for testing ---
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        print(f"Created a sample input folder: '{input_folder}'")
        try:
            # Create a dummy TIFF file for demonstration purposes
            dummy_image = Image.new('RGB', (100, 100), color = 'red')
            dummy_image.save(os.path.join(input_folder, 'example1.tiff'), 'TIFF')
            dummy_image.putpixel((50,50), (0,255,0)) # Add a green pixel
            dummy_image.save(os.path.join(input_folder, 'example2.tif'), 'TIFF')
            print("Created dummy .tiff files in the input folder for you to test.")
        except Exception as e:
            print(f"Could not create dummy tiff file. Reason: {e}")
    # --- End of dummy file creation ---
            
    convert_tiff_to_png(input_folder, output_folder)
