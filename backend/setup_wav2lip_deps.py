#!/usr/bin/env python3
"""
Installs the necessary dependencies for Wav2Lip to work.
"""
import subprocess
import sys
import os

def main():
    print("Setting up Wav2Lip dependencies...")
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to Wav2Lip requirements file
    req_path = os.path.join(script_dir, 'wav2lip', 'requirements.txt')
    
    if not os.path.exists(req_path):
        print(f"Error: Wav2Lip requirements file not found at {req_path}")
        sys.exit(1)
    
    # Install dependencies
    print(f"Installing dependencies from {req_path}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_path], check=True)
        print("Wav2Lip dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)
    
    # Install additional dependencies needed by our app
    print("Installing additional dependencies...")
    additional_deps = [
        "opencv-python",
        "sounddevice",
        "soundfile",
        "numpy",
        "scipy",
        "torch"
    ]
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install"] + additional_deps, check=True)
        print("Additional dependencies installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing additional dependencies: {e}")
        sys.exit(1)
    
    print("Setup complete! You should now be able to run the app.")

if __name__ == "__main__":
    main() 