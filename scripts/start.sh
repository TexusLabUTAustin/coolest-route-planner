#!/bin/bash
# Set library paths for Nix packages
export LD_LIBRARY_PATH=$(find /nix/store -name "libexpat.so*" -type f | head -1 | xargs dirname):$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(find /nix/store -name "libgdal.so*" -type f | head -1 | xargs dirname):$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(find /nix/store -name "libgeos*.so*" -type f | head -1 | xargs dirname):$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(find /nix/store -name "libproj.so*" -type f | head -1 | xargs dirname):$LD_LIBRARY_PATH

# Run the backend
python3 backend.py

