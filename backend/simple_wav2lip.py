import os
import sys
import cv2
import subprocess
import time
from pathlib import Path

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Create necessary directories
def ensure_directories():
    """Create necessary directories if they don't exist"""
    print("Creating necessary directories...")
    dirs = ['temp', 'library', 'audio', 'results']
    for dir_name in dirs:
        dir_path = os.path.join(script_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    print("Directories created")

# Create directory paths
audio_dir = os.path.join(script_dir, 'audio')
library_dir = os.path.join(script_dir, 'library')
temp_dir = os.path.join(script_dir, 'temp')
results_dir = os.path.join(script_dir, 'results')

# Ensure directories exist
ensure_directories()

def optimize_image_resolution(image_path, target_width=256):
    """Optimize image resolution for Wav2Lip processing"""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    
    # Calculate new dimensions while maintaining aspect ratio
    height, width = img.shape[:2]
    aspect_ratio = width / height
    new_height = int(target_width / aspect_ratio)
    
    # Resize image
    resized = cv2.resize(img, (target_width, new_height))
    
    # Save optimized image
    optimized_path = os.path.join(temp_dir, 'optimized_avatar.jpeg')
    cv2.imwrite(optimized_path, resized)
    return optimized_path

def run_wav2lip(audio_path, output_path, avatar_path=None):
    """Run the Wav2Lip model to generate a lip-synced video"""
    print(f"Starting Wav2Lip with audio: {audio_path}")
    
    # Use the specified avatar or default
    if not avatar_path:
        avatar_path = os.path.join(library_dir, "avatar.jpeg")
        if not os.path.exists(avatar_path):
            # Try png as fallback
            avatar_path = os.path.join(library_dir, "avatar.png")
            if not os.path.exists(avatar_path):
                raise FileNotFoundError(f"No avatar found at {avatar_path}")
    
    if not os.path.exists(avatar_path):
        raise FileNotFoundError(f"Input image file not found: {avatar_path}")
    
    # Optimize input image resolution
    optimized_image = optimize_image_resolution(avatar_path)
    
    # Find wav2lip directories with both case conventions
    if os.path.exists(os.path.join(script_dir, 'wav2lip')):
        wav2lip_dir = os.path.join(script_dir, 'wav2lip')
    elif os.path.exists(os.path.join(script_dir, 'Wav2Lip')):
        wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
    else:
        raise FileNotFoundError("Wav2Lip directory not found")
    
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    
    # Validate paths
    if not os.path.exists(inference_path):
        raise FileNotFoundError(f"Wav2Lip inference.py not found: {inference_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Wav2Lip checkpoint not found: {checkpoint_path}")
    
    # Try to use CUDA if available
    try:
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
    except ImportError:
        device = 'cpu'
        print("PyTorch not available, using CPU")
    
    # Optimize batch sizes based on device
    face_det_batch_size = 4 if device == 'cuda' else 1
    wav2lip_batch_size = 4 if device == 'cuda' else 1
    
    # Prepare command
    command = [
        'python', inference_path,
        '--checkpoint_path', checkpoint_path,
        '--face', optimized_image,
        '--audio', audio_path,
        '--outfile', output_path,
        '--pads', '0', '5', '0', '0',
        '--nosmooth',
        '--face_det_batch_size', str(face_det_batch_size),
        '--wav2lip_batch_size', str(wav2lip_batch_size)
    ]
    
    print(f"Running Wav2Lip command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running Wav2Lip: {result.stderr}")
            print("Trying with conda environment...")
            
            # Try fallback with explicit conda env
            conda_cmd = [
                'conda', 'run', '-n', 'kirk-ai',
                'python', inference_path,
                '--checkpoint_path', checkpoint_path,
                '--face', optimized_image,
                '--audio', audio_path,
                '--outfile', output_path,
                '--pads', '0', '5', '0', '0',
                '--nosmooth',
                '--face_det_batch_size', str(face_det_batch_size),
                '--wav2lip_batch_size', str(wav2lip_batch_size)
            ]
            print(f"Trying conda run: {' '.join(conda_cmd)}")
            result = subprocess.run(conda_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Conda run also failed: {result.stderr}")
                return None
    except Exception as e:
        print(f"Error during Wav2Lip execution: {str(e)}")
        return None
    
    # Check if the output file was created
    if not os.path.exists(output_path):
        print(f"Wav2Lip failed to generate output video: {output_path}")
        return None
    
    print(f"Wav2Lip completed successfully: {output_path}")
    return output_path

def main():
    # Make sure we have an audio file
    test_audio = os.path.join(audio_dir, "test_audio.mp3")
    if not os.path.exists(test_audio):
        from voice_to_voice.advisor import speak_text_with_elevenlabs
        print("Generating test audio...")
        test_text = "This is a test of the Wav2Lip system."
        test_audio = speak_text_with_elevenlabs(test_text, play_audio=False)
        if not test_audio:
            print("Failed to generate test audio. Please place an audio file at:", 
                  os.path.join(audio_dir, "test_audio.mp3"))
            return
    
    # Output path in the results directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(results_dir, f"wav2lip_result_{timestamp}.mp4")
    
    # Run Wav2Lip
    print(f"Running Wav2Lip with audio: {test_audio}")
    print(f"Output will be saved to: {output_path}")
    
    result = run_wav2lip(
        audio_path=test_audio,
        output_path=output_path
    )
    
    if result:
        print(f"✅ Success! Output saved to: {result}")
        print(f"You can find the result in the 'results' directory.")
    else:
        print("❌ Failed to generate video with Wav2Lip.")

if __name__ == "__main__":
    # Import elevenlabs API key
    if 'ELEVENLABS_API_KEY' not in os.environ:
        os.environ['ELEVENLABS_API_KEY'] = "sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
        os.environ['ELEVEN_LABS_API_KEY'] = "sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
    
    main() 