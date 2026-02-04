#!/usr/bin/env python3
"""
Convert UTCI GeoTIFF to .npz format for faster download and load.

Saves: values (2D int16, UTCI * scale), transform (6 floats), shape, scale (float).
At read time, values are divided by scale to get back UTCI. Using int16 + scale
reduces file size (2 bytes per pixel vs 4 for float32).

Usage:
  python convert_utci_to_npz.py [input.tif] [output.npz] [scale]
  Default: UTCI_1600.tif -> UTCI_1600.npz, scale=100 (0.01°C resolution).
  Use scale=100 so route ranks match .tif; scale=10 can flip route order.
"""

import os
import sys
import numpy as np
import rasterio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "UTCI_1600.tif")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "UTCI_1600.npz")


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0  # 0.01°C resolution; keeps route ranks in sync with .tif

    if not os.path.exists(input_path):
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    print(f"Reading {input_path}...")
    with rasterio.open(input_path) as src:
        values_float = src.read(1)
        t = src.transform
        transform = (t.a, t.b, t.c, t.d, t.e, t.f)
        shape = values_float.shape

    # Scale only the UTCI band to int16 (lat/lon come from transform, not scaled)
    values_int = np.round(values_float * scale).astype(np.int16)
    print(f"Shape: {shape}, UTCI scale: {scale} (divide value by {scale} when reading)")
    print(f"Size: int16 {values_int.nbytes / (1024*1024):.2f} MB (was float32 {values_float.nbytes / (1024*1024):.2f} MB)")
    np.savez_compressed(
        output_path,
        values=values_int,
        transform=np.array(transform, dtype=np.float64),
        shape=np.array(shape, dtype=np.int32),
        scale=np.float64(scale),
    )
    out_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Saved {output_path} ({out_size:.2f} MB)")
    print("Upload to S3 and set UTCI_NPZ_URL in Railway.")


if __name__ == "__main__":
    main()
