#!/bin/bash

# Go to the backend directory
cd "$(dirname "$0")"

# Activate the conda environment
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate kirk-ai

# Export API keys for ElevenLabs
export OPENAI_API_KEY="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"
export ELEVENLABS_API_KEY="sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
export ELEVEN_LABS_API_KEY="$ELEVENLABS_API_KEY"
export ELEVENLABS_VOICE_ID="5ERbh3mpIEzi6sfFHo7H"

# Run the simplified script
echo "🎥 Running simplified Wav2Lip script..."
python simple_wav2lip.py

# Keep terminal open when done
echo "Process completed. Press any key to close this window."
read -n 1 