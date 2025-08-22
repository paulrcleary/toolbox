# HDR to JPG with Gain Map Converter
#
# This script converts a High Dynamic Range (HDR) image in Radiance (.hdr) format
# into a standard JPEG (.jpg) file with an embedded HDR gain map.
# This allows the image to be viewed on both SDR and HDR displays appropriately.
#
# Dependencies:
# pip install numpy imageio imageio-freeimage Pillow colour-science
#
# Usage:
# python convert_with_gainmap.py <path_to_input.hdr> <path_to_output.jpg>
#
# Example:
# python convert_with_gainmap.py my_scene.hdr my_scene_with_gainmap.jpg

import sys
import os
import imageio.v2 as imageio
import numpy as np
import colour
from PIL import Image
import base64
import io
import argparse

def create_xmp_metadata(sdr_image_bytes, gain_map_image_bytes, hdr_capacity_max, gain_map_max_log2):
    """
    Constructs the XMP metadata string with an embedded gain map.
    
    The metadata follows the Adobe Gain Map specification, which is used by
    Google and Apple for HDR photos. The gain map itself is base64-encoded.
    """
    
    # Base64 encode the gain map image data
    gain_map_base64 = base64.b64encode(gain_map_image_bytes).decode('utf-8')

    # The XMP structure is XML-based. We use an f-string to build it.
    # This defines the primary image (the SDR rendition) and the secondary
    # image (the gain map) with its associated parameters.
    xmp_template = f"""
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 5.6-c148 79.164036, 2019/08/13-01:06:57        ">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:GContainer="http://ns.google.com/photos/1.0/container/"
    xmlns:GImage="http://ns.google.com/photos/1.0/image/"
    xmlns:GainMap="http://ns.adobe.com/hdr/gainmap/1.0/">
   <GContainer:Directory>
    <rdf:Seq>
     <rdf:li rdf:parseType="Resource">
      <GContainer:Item
       GContainer:Mime="image/jpeg"
       GContainer:Semantic="Primary"/>
     </rdf:li>
     <rdf:li rdf:parseType="Resource">
      <GContainer:Item
       GContainer:Mime="image/jpeg"
       GContainer:Semantic="GainMap"/>
      <GainMap:Version>1.0</GainMap:Version>
      <GainMap:GainMapMin>0.0, 0.0, 0.0</GainMap:GainMapMin>
      <GainMap:GainMapMax>{gain_map_max_log2:.6f}, {gain_map_max_log2:.6f}, {gain_map_max_log2:.6f}</GainMap:GainMapMax>
      <GainMap:Gamma>1.0, 1.0, 1.0</GainMap:Gamma>
      <GainMap:OffsetSDR>0.0, 0.0, 0.0</GainMap:OffsetSDR>
      <GainMap:OffsetHDR>0.0, 0.0, 0.0</GainMap:OffsetHDR>
      <GainMap:HDRCapacityMin>0.0</GainMap:HDRCapacityMin>
      <GainMap:HDRCapacityMax>{hdr_capacity_max:.6f}</GainMap:HDRCapacityMax>
      <GImage:Data>{gain_map_base64}</GImage:Data>
     </rdf:li>
    </rdf:Seq>
   </GContainer:Directory>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
"""
    return xmp_template.encode('utf-8')


def convert_hdr_to_jpg_with_gainmap(hdr_path, jpg_path, quality=95):
    """
    Main conversion function.
    
    Args:
        hdr_path (str): Path to the input Radiance HDR file.
        jpg_path (str): Path for the output JPG file.
        quality (int): JPEG quality for both SDR image and gain map.
    """
    print(f"Loading HDR image from: {hdr_path}")

    # --- 1. Validate Path and Load HDR image ---
    # Add a check to see if the file exists before trying to read it.
    # This provides a clearer error than the generic 'cannot handle uri' message.
    if not os.path.exists(hdr_path):
        print(f"Error: Input file not found at the specified path.")
        print(f"Attempted to read from absolute path: '{os.path.abspath(hdr_path)}'")
        return

    try:
        # Load HDR image. Radiance files are typically in linear color space.
        hdr_image_linear = imageio.imread(hdr_path, format='HDR-FI')
        # Ensure it's float32 for processing
        hdr_image_linear = hdr_image_linear.astype(np.float32)
    except Exception as e:
        print(f"Error reading HDR file: {e}")
        print("\nThis could be due to several reasons:")
        print("1. The file is corrupted or not a valid Radiance HDR format.")
        print("2. The 'imageio-freeimage' plugin is not installed correctly or has an issue.")
        print("3. File permissions are preventing access.")
        return

    # --- 2. Create SDR Rendition via Tone-Mapping ---
    print("Creating SDR rendition using tone-mapping...")
    # We use a simple but effective tone-mapping operator from colour-science.
    # This compresses the high dynamic range into a standard range.
    sdr_image_linear = colour.models.tonemapping_operator_Reinhard2005(hdr_image_linear, Y_d=0.2)

    # The SDR image data is still linear. We need to apply a gamma correction
    # (sRGB EOTF) to make it look correct on a standard display.
    sdr_image_gamma = np.clip(colour.models.eotf_inverse_sRGB(sdr_image_linear), 0, 1)
    
    # Convert to 8-bit integer format for saving as JPEG
    sdr_image_uint8 = (sdr_image_gamma * 255).astype(np.uint8)

    # --- 3. Calculate the Gain Map ---
    print("Calculating gain map...")
    # The gain map stores the ratio of HDR to SDR brightness in log space.
    # We use log2 for this calculation.
    # Add a small epsilon to avoid division by zero in pure black areas.
    epsilon = 1e-6
    
    # Calculate gain in linear space
    gain = hdr_image_linear / (sdr_image_linear + epsilon)
    
    # Convert to log2 space. The gain map stores how many "stops" of light to add.
    log2_gain_map = np.log2(np.maximum(gain, 1.0)) # We only care about gains > 1

    # Find the maximum values for metadata. This tells the renderer the range of the map.
    gain_map_max_log2 = np.max(log2_gain_map)
    hdr_capacity_max = gain_map_max_log2
    
    # Normalize the gain map to the [0, 1] range for saving as an image.
    gain_map_normalized = log2_gain_map / gain_map_max_log2 if gain_map_max_log2 > 0 else np.zeros_like(log2_gain_map)
    
    # Convert to 8-bit for saving as a grayscale JPEG
    gain_map_uint8 = (gain_map_normalized * 255).astype(np.uint8)
    
    # The gain map is often a single channel (grayscale) image.
    # We can get it from any of the RGB channels as they are usually correlated.
    # Using the 'L' mode in Pillow handles this correctly.
    gain_map_image = Image.fromarray(gain_map_uint8[:,:,0], mode='L')
    
    # --- 4. Save Images to In-Memory Buffers ---
    print("Encoding images and metadata...")
    # We need the byte data of the SDR image and the gain map image to embed them.
    
    # Save SDR image to a buffer
    sdr_buffer = io.BytesIO()
    Image.fromarray(sdr_image_uint8).save(sdr_buffer, format='JPEG', quality=quality)
    sdr_image_bytes = sdr_buffer.getvalue()

    # Save Gain Map image to a buffer
    gain_map_buffer = io.BytesIO()
    # The gain map can be saved at a lower resolution and quality to save space
    # Here we resize it to half the original dimensions.
    w, h = gain_map_image.size
    gain_map_image.resize((w // 2, h // 2)).save(gain_map_buffer, format='JPEG', quality=quality)
    gain_map_image_bytes = gain_map_buffer.getvalue()

    # --- 5. Create XMP Metadata and Save Final JPG ---
    xmp_data = create_xmp_metadata(
        sdr_image_bytes,
        gain_map_image_bytes,
        hdr_capacity_max,
        gain_map_max_log2
    )

    # Use Pillow to save the final JPG with the embedded XMP data
    sdr_pil_image = Image.open(io.BytesIO(sdr_image_bytes))
    
    print(f"Saving final JPG with embedded gain map to: {jpg_path}")
    sdr_pil_image.save(jpg_path, format='JPEG', quality=quality, xmp=xmp_data)
    
    print("Conversion complete.")


if __name__ == '__main__':
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Converts a Radiance HDR (.hdr) file to a JPG with an embedded gain map."
    )
    parser.add_argument(
        "input_hdr", 
        help="Path to the input HDR file."
    )
    parser.add_argument(
        "output_jpg", 
        help="Path for the output JPG file."
    )
    parser.add_argument(
        "--quality", 
        type=int, 
        default=95, 
        help="JPEG quality for the output file (0-100)."
    )

    # Gracefully exit if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()
    
    convert_hdr_to_jpg_with_gainmap(args.input_hdr, args.output_jpg, args.quality)
