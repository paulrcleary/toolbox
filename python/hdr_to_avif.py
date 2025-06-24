#!/usr/bin/env python3

import argparse
import sys
import traceback
from pathlib import Path

try:
    import numpy as np
    import imageio.v3 as iio
    import pyavif
except ImportError as e:
    print(f"Error importing necessary libraries: {e}")
    print("Please ensure numpy, imageio, and pyavif are installed:")
    print("  pip install numpy imageio pyavif Pillow")
    sys.exit(1)

# Define standard HDR mastering display metadata (BT.2020 primaries, D65 white point)
# Using typical luminance values for HDR10 (max 1000 nits, min 0.0001 nits)
DEFAULT_MASTERING_DISPLAY = pyavif.MasteringDisplay(
    primaries=pyavif.DisplayPrimaries(0.680, 0.320, 0.265, 0.690, 0.150, 0.060), # BT.2020
    white_point=pyavif.DisplayPrimaries.D65, # D65
    max_luminance=1000.0,
    min_luminance=0.0001
)

def convert_hdr_to_avif(
    hdr_path: Path,
    avif_path: Path,
    quality: int,
    speed: int,
    depth: int,
    yuv_format_str: str,
    max_cll: int | None,
    max_fall: int | None,
    overwrite: bool = False
):
    """
    Converts a single HDR Radiance file to AVIF with HDR metadata.

    Args:
        hdr_path: Path to the input HDR file.
        avif_path: Path to the output AVIF file.
        quality: AVIF encoding quality (0-63, lower is higher quality).
        speed: AVIF encoding speed (0-10, lower is slower/better quality).
        depth: Bit depth for encoding (8, 10, or 12).
        yuv_format_str: Chroma subsampling ('444', '422', '420').
        max_cll: Maximum Content Light Level (nits), optional.
        max_fall: Maximum Frame Average Light Level (nits), optional.
        overwrite: Whether to overwrite existing output files.
    """
    if not hdr_path.is_file():
        print(f"Error: Input HDR file not found: {hdr_path}")
        return False

    if avif_path.exists() and not overwrite:
        print(f"Skipping: Output file already exists: {avif_path}")
        return True # Not an error, just skipping

    print(f"Processing: {hdr_path.name} -> {avif_path.name}")

    try:
        # 1. Read HDR file using imageio
        # This typically returns a float32 numpy array with linear RGB data
        img_hdr = iio.imread(hdr_path, plugin='HDR-FI') # Try forcing FreeImage HDR plugin

        if not np.issubdtype(img_hdr.dtype, np.floating):
             # If not float, try reading without specific plugin hint
             print(f"Warning: Read data type is {img_hdr.dtype}, expected float. Retrying read...")
             img_hdr = iio.imread(hdr_path)
             if not np.issubdtype(img_hdr.dtype, np.floating):
                 print(f"Error: Could not read HDR file '{hdr_path}' as floating point data.")
                 return False

        # Ensure 3 channels (RGB)
        if img_hdr.ndim == 2: # Grayscale
             print("Warning: Input image is grayscale. Converting to RGB.")
             img_hdr = np.stack((img_hdr,) * 3, axis=-1)
        elif img_hdr.ndim != 3 or img_hdr.shape[2] != 3:
             print(f"Error: Unexpected image shape {img_hdr.shape}. Expected HxWx3.")
             return False

        print(f"  Input details: shape={img_hdr.shape}, dtype={img_hdr.dtype}, "
              f"min={np.min(img_hdr):.2f}, max={np.max(img_hdr):.2f}")

        # 2. Prepare AVIF encoding options
        yuv_format_map = {
            '444': pyavif.YUVFormat.YUV444,
            '422': pyavif.YUVFormat.YUV422,
            '420': pyavif.YUVFormat.YUV420,
        }
        yuv_format = yuv_format_map.get(yuv_format_str)
        if yuv_format is None:
            print(f"Error: Invalid YUV format '{yuv_format_str}'. Use '444', '422', or '420'.")
            return False

        # Content Light Level Information (optional)
        clli = None
        if max_cll is not None and max_fall is not None:
            clli = pyavif.ContentLightLevelInformation(
                max_cll=max_cll, max_fall=max_fall
            )
            print(f"  Using CLLI: MaxCLL={max_cll}, MaxFALL={max_fall}")
        elif max_cll is not None or max_fall is not None:
             print("Warning: Both --max_cll and --max_fall must be provided to set CLLI metadata. Ignoring.")


        # 3. Encode to AVIF using pyavif
        # pyavif handles the conversion from linear float RGB to YCbCr internally
        # We specify the target HDR characteristics (PQ transfer, BT.2020 primaries)
        avif_bytes = pyavif.encode(
            img_hdr,
            quality=quality,        # libavif quality (0-63), lower means better quality
            speed=speed,            # Encoding speed (0-10), lower means slower/better compression
            depth=depth,            # Bit depth (10 or 12 recommended for HDR)
            yuv_format=yuv_format,  # Chroma subsampling
            range='full',           # Input data range ('full' for float)

            # --- HDR Metadata ---
            matrix_coefficients=pyavif.MatrixCoefficients.BT2020_NCL, # BT.2020 Non-constant Luminance
            color_primaries=pyavif.ColorPrimaries.BT2020,           # BT.2020 Primaries
            transfer_characteristics=pyavif.TransferCharacteristics.PQ, # PQ (ST 2084) Transfer Function
            mastering_display=DEFAULT_MASTERING_DISPLAY,            # Assumed mastering display
            clli=clli                                               # Content Light Level Info (optional)
        )

        # 4. Write the AVIF file
        avif_path.parent.mkdir(parents=True, exist_ok=True) # Ensure output dir exists
        avif_path.write_bytes(avif_bytes)

        print(f"Successfully converted to {avif_path}")
        return True

    except FileNotFoundError:
        print(f"Error: Input file not found at {hdr_path}")
        return False
    except iio.core.fetching.UnidentifiedImageError:
        print(f"Error: Could not read or identify image file: {hdr_path}")
        print("Ensure it's a valid Radiance HDR file and imageio has the correct plugin.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while processing {hdr_path}:")
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert HDR Radiance (.hdr) files to AVIF format with HDR metadata.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to the input HDR file or a directory containing HDR files."
    )
    parser.add_argument(
        "output_path",
        type=str,
        help="Path to the output AVIF file or a directory where AVIF files will be saved."
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=25, # Corresponds roughly to libavif CQ 25, a good balance.
        help="AVIF quality level (0-63, lower value means higher quality, lossless is 0)."
    )
    parser.add_argument(
        "-s", "--speed",
        type=int,
        default=4, # A good balance between speed and compression efficiency.
        help="AVIF encoding speed (0-10, lower value means slower encoding but potentially better compression)."
    )
    parser.add_argument(
        "-d", "--depth",
        type=int,
        default=10,
        choices=[8, 10, 12],
        help="Bit depth for AVIF encoding (10 or 12 recommended for HDR)."
    )
    parser.add_argument(
        "--yuv_format",
        type=str,
        default="444",
        choices=['444', '422', '420'],
        help="Chroma subsampling format (444 preserves most color detail)."
    )
    parser.add_argument(
        "--max_cll",
        type=int,
        default=None,
        help="Maximum Content Light Level (MaxCLL) in nits (optional HDR metadata)."
    )
    parser.add_argument(
        "--max_fall",
        type=int,
        default=None,
        help="Maximum Frame Average Light Level (MaxFALL) in nits (optional HDR metadata)."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files."
    )

    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)

    files_to_process = []
    output_is_dir = False

    if input_path.is_file():
        if not input_path.suffix.lower() == '.hdr':
            print(f"Error: Input file '{input_path}' does not have a .hdr extension.")
            sys.exit(1)
        # If output path ends with / or \ or exists as a directory, treat it as a directory
        if str(output_path).endswith(('/', '\')) or output_path.is_dir():
             output_is_dir = True
             output_target = output_path / input_path.with_suffix('.avif').name
        else:
             # Treat output as a specific file path
             output_target = output_path
             # Ensure output directory exists if specified like dir/output.avif
             output_target.parent.mkdir(parents=True, exist_ok=True)

        files_to_process.append((input_path, output_target))

    elif input_path.is_dir():
        output_is_dir = True
        if output_path.exists() and not output_path.is_dir():
            print(f"Error: Input is a directory, but output path '{output_path}' exists and is not a directory.")
            sys.exit(1)
        output_path.mkdir(parents=True, exist_ok=True) # Ensure output dir exists

        print(f"Scanning directory: {input_path}")
        count = 0
        for item in input_path.rglob('*.hdr'):
            if item.is_file():
                output_target = output_path / item.relative_to(input_path).with_suffix('.avif')
                files_to_process.append((item, output_target))
                count += 1
        print(f"Found {count} .hdr files.")
        if count == 0:
             sys.exit(0) # Nothing to do

    else:
        print(f"Error: Input path is neither a file nor a directory: {input_path}")
        sys.exit(1)


    # Process files
    success_count = 0
    fail_count = 0
    skip_count = 0

    for hdr_file, avif_file in files_to_process:
         # Check for overwrite condition specifically here
         if avif_file.exists() and not args.overwrite:
             print(f"Skipping: Output file already exists: {avif_file}")
             skip_count += 1
             continue

         # Ensure the specific output directory for this file exists if processing a directory
         if output_is_dir:
              avif_file.parent.mkdir(parents=True, exist_ok=True)

         result = convert_hdr_to_avif(
             hdr_file,
             avif_file,
             args.quality,
             args.speed,
             args.depth,
             args.yuv_format,
             args.max_cll,
             args.max_fall,
             args.overwrite # Pass overwrite flag to function (though checked before call too)
         )
         if result:
             success_count += 1
         else:
             fail_count += 1

    print("\n--- Conversion Summary ---")
    print(f"Successfully converted: {success_count}")
    print(f"Skipped (already exist): {skip_count}")
    print(f"Failed: {fail_count}")
    print("------------------------")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
