#!/bin/bash

# Go to the backend directory
cd "$(dirname "$0")"

# Activate the conda environment
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate kirk-ai

# Run the super simple script
echo "🎥 Running super simple Wav2Lip script..."
python super_simple_wav2lip.py 