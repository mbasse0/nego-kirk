#!/usr/bin/env python3
"""
Test script for running Wav2Lip directly using the approach from your working code
"""

import os
import sys
import subprocess
import cv2
import soundfile as sf
import numpy as np

def optimize_image_resolution(image_path, target_width=256):
    """Optimize image resolution for Wav2Lip processing"""
    print(f"Reading image: {image_path}")
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    
    print(f"Image shape: {img.shape}")
    
    # Calculate new dimensions while maintaining aspect ratio
    height, width = img.shape[:2]
    aspect_ratio = width / height
    new_height = int(target_width / aspect_ratio)
    
    # Resize image
    resized = cv2.resize(img, (target_width, new_height))
    
    # Save optimized image
    optimized_path = os.path.join('temp', 'optimized_avatar.png')
    os.makedirs('temp', exist_ok=True)
    cv2.imwrite(optimized_path, resized)
    print(f"Saved optimized image to: {optimized_path}")
    return optimized_path

def run_wav2lip_test():
    print("\n=== Testing Wav2Lip Direct Execution ===\n")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
    
    # Check if Wav2Lip directory exists
    if not os.path.exists(wav2lip_dir):
        print(f"Error: Wav2Lip directory not found at {wav2lip_dir}")
        return False
    
    # First check if the audio.py module exists and can be imported
    audio_py = os.path.join(wav2lip_dir, 'audio.py')
    if not os.path.exists(audio_py):
        print(f"Error: audio.py not found at {audio_py}")
        return False
    
    # Add Wav2Lip to the Python path
    sys.path.append(wav2lip_dir)
    print(f"Added {wav2lip_dir} to Python path")
    
    # Try importing audio module
    try:
        print("Attempting to import audio.py...")
        sys.path.insert(0, script_dir)  # Make sure current directory is in path
        from Wav2Lip import audio
        print("Successfully imported audio module")
    except ImportError as e:
        print(f"Error importing audio module: {e}")
        print("\nTrying to fix by copying audio.py...")
        
        # Copy audio.py to current directory as a fallback
        import shutil
        try:
            shutil.copy2(audio_py, os.path.join(script_dir, 'audio.py'))
            print("Copied audio.py to current directory")
            
            # Try importing again
            try:
                import audio
                print("Successfully imported audio module from current directory")
            except ImportError as e2:
                print(f"Still unable to import audio module: {e2}")
                return False
        except Exception as e:
            print(f"Error copying audio.py: {e}")
            return False
    
    # Check for test audio and image files
    audio_dir = os.path.join(script_dir, 'audio')
    library_dir = os.path.join(script_dir, 'library')
    
    # Find an mp3 file to use for testing
    mp3_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    if not mp3_files:
        print("No mp3 files found in audio directory!")
        return False
    
    audio_file = os.path.join(audio_dir, mp3_files[0])
    print(f"Using audio file: {audio_file}")
    
    # Check for avatar image
    avatar_file = os.path.join(library_dir, 'avatar.png')
    if not os.path.exists(avatar_file):
        avatar_file = os.path.join(library_dir, 'avatar.jpeg')
        if not os.path.exists(avatar_file):
            print("No avatar image found!")
            return False
    
    print(f"Using avatar file: {avatar_file}")
    
    # Optimize the image
    try:
        optimized_image = optimize_image_resolution(avatar_file)
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return False
    
    # Set up checkpoint path
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    if not os.path.exists(checkpoint_path):
        print(f"Checkpoint file not found at {checkpoint_path}")
        return False
    
    # Set up output path
    output_path = os.path.join(script_dir, 'output', 'test_output.mp4')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Check if CUDA is available
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"CUDA available: {cuda_available}")
    except ImportError:
        print("PyTorch not available")
        cuda_available = False
    
    # Set batch sizes
    face_det_batch_size = 4 if cuda_available else 1
    wav2lip_batch_size = 4 if cuda_available else 1
    
    # Get the Python executable from sys.executable
    python_path = sys.executable
    print(f"Using Python: {python_path}")
    
    # Setup command
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    command = [
        python_path,
        inference_path,
        "--checkpoint_path", checkpoint_path,
        "--face", optimized_image,
        "--audio", audio_file,
        "--outfile", output_path,
        "--pads", "0", "5", "0", "0",
        "--nosmooth",
        "--face_det_batch_size", str(face_det_batch_size),
        "--wav2lip_batch_size", str(wav2lip_batch_size)
    ]
    
    print("\nRunning Wav2Lip command:")
    print(" ".join(command))
    
    # Execute the command
    try:
        # Set environment variables to ensure Python can find modules
        env = os.environ.copy()
        # Add current directory and Wav2Lip directory to PYTHONPATH
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{script_dir}:{wav2lip_dir}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = f"{script_dir}:{wav2lip_dir}"
        
        print(f"Setting PYTHONPATH to: {env['PYTHONPATH']}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=env
        )
        
        print("\nCommand output:")
        print(result.stdout)
        
        if result.returncode != 0:
            print("\nCommand failed with error:")
            print(result.stderr)
            return False
        
        # Check if output file was created
        if os.path.exists(output_path):
            print(f"\nSuccess! Output video created at: {output_path}")
            print(f"File size: {os.path.getsize(output_path)} bytes")
            return True
        else:
            print(f"\nError: Output file not created at {output_path}")
            return False
            
    except Exception as e:
        print(f"\nError running command: {e}")
        return False

if __name__ == "__main__":
    if run_wav2lip_test():
        print("\n✅ Wav2Lip test successful!")
        sys.exit(0)
    else:
        print("\n❌ Wav2Lip test failed")
        sys.exit(1) 