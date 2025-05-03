#!/bin/bash

# Activate the conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate kirk-ai

# Set API keys (replace these with your actual keys)
export OPENAI_API_KEY="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"
export ELEVENLABS_API_KEY="sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
export ELEVENLABS_VOICE_ID="5ERbh3mpIEzi6sfFHo7H"

# Run combined_pipeline.py
echo "Running combined_pipeline.py..."
cd $(dirname "$0")
python combined_pipeline.py

# If the script exits, don't close the terminal immediately
echo "Script finished. Press any key to exit."
read -n 1 