#!/bin/bash

# Go to the backend directory
cd "$(dirname "$0")"

# Activate the conda environment (kirk-ai works with combined_pipeline.py)
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate kirk-ai

# Export API keys for both main.py and voice_to_voice modules
export OPENAI_API_KEY="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"
export ELEVENLABS_API_KEY="sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
export ELEVENLABS_VOICE_ID="5ERbh3mpIEzi6sfFHo7H"

# Also export with the alternate name for voice_to_voice modules
export ELEVEN_LABS_API_KEY="$ELEVENLABS_API_KEY"

# Start the FastAPI server with full logging
echo "🚀 Starting FastAPI server with uvicorn..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug

# If the server crashes, don't close the terminal immediately
echo "Server stopped. Press any key to exit."
read -n 1 