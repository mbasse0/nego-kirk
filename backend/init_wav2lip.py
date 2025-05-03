#!/usr/bin/env python3
"""
Initialization script for Wav2Lip
This ensures that the audio.py module can be imported correctly
"""

import os
import sys
import shutil
from pathlib import Path

def main():
    print("Initializing Wav2Lip setup...")
    
    # Get the directory of this script
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Check for Wav2Lip directory with different capitalizations
    wav2lip_candidates = [
        script_dir / "Wav2Lip",
        script_dir / "wav2lip",
        script_dir / "WAV2LIP"
    ]
    
    wav2lip_dir = None
    for candidate in wav2lip_candidates:
        if candidate.exists():
            wav2lip_dir = candidate
            print(f"Found Wav2Lip directory at: {wav2lip_dir}")
            break
    
    if wav2lip_dir is None:
        print("Error: Wav2Lip directory not found!")
        return False
    
    # Check if audio.py exists in the Wav2Lip directory
    audio_py_src = wav2lip_dir / "audio.py"
    if not audio_py_src.exists():
        print(f"Error: audio.py not found at {audio_py_src}")
        return False
    
    # Copy audio.py to the workspace directory
    audio_py_dest = script_dir / "audio.py"
    try:
        shutil.copy2(audio_py_src, audio_py_dest)
        print(f"Successfully copied audio.py to {audio_py_dest}")
    except Exception as e:
        print(f"Error copying audio.py: {str(e)}")
        return False
    
    # Create an __init__.py file in the Wav2Lip directory to make it a proper package
    init_py = wav2lip_dir / "__init__.py"
    if not init_py.exists():
        try:
            with open(init_py, 'w') as f:
                f.write("# This file makes the directory a Python package\n")
            print(f"Created __init__.py in {wav2lip_dir}")
        except Exception as e:
            print(f"Error creating __init__.py: {str(e)}")
    
    # Add the current directory to PYTHONPATH
    sys.path.insert(0, str(script_dir))
    
    # Test import
    try:
        import audio
        print("Success: audio module can be imported!")
        return True
    except ImportError as e:
        print(f"Error importing audio module: {str(e)}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1) 