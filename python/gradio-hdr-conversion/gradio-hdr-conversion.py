# To run this code, you may need to install the following libraries:
# pip install gradio numpy pillow imageio scikit-image
# This version of the app uses a low-resolution image for previews to improve
# performance and the full-resolution image for the final save.

import gradio as gr
import numpy as np
from PIL import Image
import imageio.v3 as iio
import io
import os
# Use scikit-image for HSV conversion and luminance calculation to avoid import conflicts
from skimage import color as sk_color
from skimage.transform import resize
from skimage.exposure import rescale_intensity

# --- Helper Functions ---

def linear_to_srgb(linear_image):
    """
    Converts a linear RGB image to sRGB color space.
    """
    srgb_image = np.where(linear_image <= 0.0031308,
                          linear_image * 12.92,
                          1.055 * (linear_image**(1/2.4)) - 0.055)
    return np.clip(srgb_image, 0, 1)

def apply_adjustments(hdr_data, contrast, exposure, saturation):
    """
    Applies contrast, exposure, and saturation adjustments to HDR data.

    Args:
        hdr_data (np.array): The input HDR image data (linear RGB).
        contrast (float): A value to multiply the image by.
        exposure (float): An exposure compensation value (log2 scale).
        saturation (float): Saturation adjustment factor.

    Returns:
        np.array: The adjusted HDR image data.
    """
    # Apply exposure compensation
    adjusted_hdr = hdr_data * (2 ** exposure)

    # Convert to HSV color space for saturation adjustment using skimage
    hsv_data = sk_color.rgb2hsv(adjusted_hdr)
    
    # Adjust saturation (the second channel in HSV)
    hsv_data[..., 1] *= saturation
    hsv_data[..., 1] = np.clip(hsv_data[..., 1], 0, 1) # Ensure saturation is within a valid range

    # Convert back to RGB
    adjusted_hdr = sk_color.hsv2rgb(hsv_data)

    # Apply contrast - a simple power curve
    adjusted_hdr = adjusted_hdr ** (1/contrast)

    return adjusted_hdr

def reinhard_tone_mapping(hdr_data):
    """
    Applies a simple global Reinhard tone mapping operator.
    Formula: L_out = L_in / (1 + L_in)
    """
    # Calculate luminance from linear RGB data
    luminance = sk_color.rgb2gray(hdr_data)
    
    # Apply the Reinhard formula to luminance
    luminance_out = luminance / (1 + luminance)
    
    # Scale the original HDR image by the ratio of the new and old luminance
    # to maintain color integrity
    scale_factor = np.where(luminance > 0, luminance_out / luminance, 0)
    toned_data = hdr_data * scale_factor[..., np.newaxis]
    
    return toned_data

def tone_map_to_sdr(hdr_data):
    """
    Performs tone mapping from HDR to SDR.
    This function now uses the manual Reinhard tone mapping implementation.

    Args:
        hdr_data (np.array): The HDR image data (linear RGB).

    Returns:
        np.array: The tone-mapped SDR image data (linear RGB, 0-1 range).
    """
    return reinhard_tone_mapping(hdr_data)

def generate_gain_map(hdr_data, sdr_data):
    """
    Generates a gain map by calculating the ratio of HDR to SDR luminance.
    The gain map is a grayscale image.

    Args:
        hdr_data (np.array): The original HDR data (linear RGB).
        sdr_data (np.array): The tone-mapped SDR data (linear RGB).

    Returns:
        np.array: The gain map data (normalized 0-1).
    """
    # Calculate luminance for both images using a standard formula
    def get_luminance(rgb_data):
        return 0.2126 * rgb_data[..., 0] + 0.7152 * rgb_data[..., 1] + 0.0722 * rgb_data[..., 2]

    hdr_luminance = get_luminance(hdr_data)
    sdr_luminance = get_luminance(sdr_data)

    # Avoid division by zero
    sdr_luminance[sdr_luminance == 0] = 1e-6

    # Calculate the ratio (gain) and normalize it to the 0-1 range
    gain_map = hdr_luminance / sdr_luminance
    gain_map = np.clip(gain_map, 0, 100) # Clip to a reasonable range
    gain_map = gain_map / np.max(gain_map) # Normalize to 0-1 for display

    return gain_map

def convert_to_pil_image(image_data, is_hdr_preview=False, gain_map_data=None):
    """
    Converts a NumPy array to a Pillow Image object.
    If it's an HDR preview, it will use the gain map to create a visual
    representation of the HDR content.
    """
    if is_hdr_preview and gain_map_data is not None:
        # A more pronounced visualization of the HDR preview.
        # This multiplies the SDR image by the gain map to show
        # where the highlights are. This is not a true HDR representation.
        sdr_data = image_data
        visualized_hdr = np.clip(sdr_data * gain_map_data[:, :, np.newaxis] * 5, 0, 1)
        srgb_image = linear_to_srgb(visualized_hdr)
    else:
        srgb_image = linear_to_srgb(image_data)

    # Convert to 8-bit integer format for Pillow
    srgb_8bit = (srgb_image * 255).astype(np.uint8)
    return Image.fromarray(srgb_8bit)


# --- Main Gradio Functions ---

def load_hdr_file(hdr_file):
    """
    Loads the high-res HDR file and creates a low-res version for previews.
    Returns both high-res and low-res data.
    """
    if hdr_file is None:
        return None, None, None, None
    
    try:
        # Read the high-res HDR file
        high_res_hdr_data = iio.imread(hdr_file.name)
        if high_res_hdr_data.ndim != 3 or high_res_hdr_data.shape[2] != 3:
            return None, None, None, "Error: Invalid image format. Please upload a 3-channel HDR file."

        # Create a low-res version for faster previews while maintaining aspect ratio
        preview_height = 512
        low_res_width = int(high_res_hdr_data.shape[1] * preview_height / high_res_hdr_data.shape[0])
        low_res_size = (preview_height, low_res_width)
        low_res_hdr_data = resize(high_res_hdr_data, low_res_size, anti_aliasing=True)
        
        # Process the low-res image for initial preview
        adjusted_hdr = apply_adjustments(low_res_hdr_data, 1.0, 0.0, 1.0)
        sdr_data = tone_map_to_sdr(adjusted_hdr)
        gain_map_data = generate_gain_map(adjusted_hdr, sdr_data)
        preview_image = convert_to_pil_image(sdr_data, False, gain_map_data)

        return low_res_hdr_data, high_res_hdr_data, preview_image, None
    except Exception as e:
        return None, None, None, f"An error occurred: {e}"

def process_and_preview(low_res_hdr_data, contrast, exposure, saturation, show_hdr_preview):
    """
    Main function to process the LOW-RES image and generate the preview images.
    """
    if low_res_hdr_data is None:
        return None, "Please upload an HDR file first."

    try:
        # Apply user adjustments to the LOW-RES data
        adjusted_hdr = apply_adjustments(low_res_hdr_data, contrast, exposure, saturation)

        # Tone map to SDR
        sdr_data = tone_map_to_sdr(adjusted_hdr)

        # Generate the gain map
        gain_map_data = generate_gain_map(adjusted_hdr, sdr_data)

        # Convert to a Pillow Image for the preview
        preview_image = convert_to_pil_image(sdr_data, show_hdr_preview, gain_map_data)

        return preview_image, None
    except Exception as e:
        return None, f"An error occurred: {e}"


def save_image_with_gain_map(high_res_hdr_data, contrast, exposure, saturation):
    """
    Saves the final HIGH-RES image as a JPEG with a gain map.
    """
    if high_res_hdr_data is None:
        return None, "Please upload an HDR file first."

    try:
        # Re-process the HIGH-RES image to ensure the final saved version
        adjusted_hdr = apply_adjustments(high_res_hdr_data, contrast, exposure, saturation)
        sdr_data = tone_map_to_sdr(adjusted_hdr)
        srgb_image = linear_to_srgb(sdr_data)
        gain_map_data = generate_gain_map(adjusted_hdr, sdr_data)

        # Create Pillow images
        sdr_pil = Image.fromarray((srgb_image * 255).astype(np.uint8))
        gain_map_pil = Image.fromarray((gain_map_data * 255).astype(np.uint8))

        # We will save the gain map as a separate file for demonstration
        # as native embedding is complex and library-dependent.
        # This is a simplified approach for demonstration purposes.
        # In a real app, you would use a library that supports the
        # specific gain map metadata format (e.g., AOM's JXL or the
        # Ultra HDR JPEG format).
        temp_dir = "temp_output"
        os.makedirs(temp_dir, exist_ok=True)
        sdr_path = os.path.join(temp_dir, "output_sdr.jpg")
        gain_map_path = os.path.join(temp_dir, "output_gain_map.jpg")

        sdr_pil.save(sdr_path, "JPEG")
        gain_map_pil.save(gain_map_path, "JPEG")

        return sdr_path, f"Saved SDR image to {sdr_path} and gain map to {gain_map_path}."

    except Exception as e:
        return None, f"An error occurred: {e}"


# --- Gradio Interface ---

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# HDR Radiance to JPEG with Gain Map")
    gr.Markdown("Upload a `.hdr` file, adjust the sliders, and save your final image.")

    # State variables to hold high and low resolution image data
    low_res_state = gr.State()
    high_res_state = gr.State()

    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="Upload HDR Image (.hdr)", type="filepath")
            contrast_slider = gr.Slider(minimum=0.5, maximum=2.0, value=1.0, step=0.1, label="Contrast", interactive=True)
            exposure_slider = gr.Slider(minimum=-3.0, maximum=3.0, value=0.0, step=0.1, label="Exposure", interactive=True)
            saturation_slider = gr.Slider(minimum=0.0, maximum=2.0, value=1.0, step=0.1, label="Saturation", interactive=True)
            toggle_preview = gr.Checkbox(label="Show HDR Preview (Visualized)")

            save_button = gr.Button("Save as JPG with Gain Map")

        with gr.Column(scale=2):
            preview_output = gr.Image(label="Image Preview")
            status_message = gr.Textbox(label="Status")
            file_output = gr.File(label="Download Saved Image")

    # Define the interactions
    # Inputs for loading the file. Note the additional state outputs.
    load_inputs = [file_input]
    load_outputs = [low_res_state, high_res_state, preview_output, status_message]
    file_input.change(fn=load_hdr_file, inputs=load_inputs, outputs=load_outputs)

    # Inputs for preview updates. Note the low-res state input.
    preview_inputs = [low_res_state, contrast_slider, exposure_slider, saturation_slider, toggle_preview]
    preview_outputs = [preview_output, status_message]
    
    # Update preview automatically when sliders change
    contrast_slider.change(fn=process_and_preview, inputs=preview_inputs, outputs=preview_outputs)
    exposure_slider.change(fn=process_and_preview, inputs=preview_inputs, outputs=preview_outputs)
    saturation_slider.change(fn=process_and_preview, inputs=preview_inputs, outputs=preview_outputs)
    
    # Toggle HDR preview without re-processing the image
    toggle_preview.change(fn=process_and_preview, inputs=preview_inputs, outputs=preview_outputs)

    # Save button interaction. Note the high-res state input.
    save_button.click(fn=save_image_with_gain_map,
                      inputs=[high_res_state, contrast_slider, exposure_slider, saturation_slider],
                      outputs=[file_output, status_message])

# Launch the app
if __name__ == "__main__":
    demo.launch()

