import os
import subprocess
print("Debug: Basic imports done")

import sys
print("Debug: sys imported")

import cv2
print("Debug: OpenCV imported")

import sounddevice as sd
print("Debug: sounddevice imported")

import soundfile as sf
print("Debug: soundfile imported")

import time
print("Debug: time imported")

import hashlib
import json
from pathlib import Path

# Add voice_to_voice directory to Python path
voice_to_voice_path = os.path.join(os.path.dirname(__file__), 'voice_to_voice')
sys.path.append(voice_to_voice_path)
print(f"Debug: Added {voice_to_voice_path} to Python path")

# Import from voice_to_voice directory one by one
print("Debug: Starting voice_to_voice imports...")

print("Debug: Importing speech_to_text...")
from speech_to_text import record_audio, transcribe_audio
print("Debug: speech_to_text imported")

print("Debug: Importing advisor...")
from advisor import speak_text_with_elevenlabs
print("Debug: advisor imported")

print("Debug: Importing kirk_agent...")
from kirk_agent import get_kirk_text
print("Debug: kirk_agent imported")

print("Debug: Importing config...")
from config import OPENAI_API_KEY, SYSTEM_PROMPT
print("Debug: config imported")

print("Debug: All imports completed successfully")

# Initialize conversation
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def ensure_directories():
    """Create necessary directories if they don't exist"""
    print("Debug: Creating directories...")
    dirs = ['temp', 'library']
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
    print("Debug: Directories created")

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
    optimized_path = os.path.join('temp', 'optimized_avatar.jpeg')
    cv2.imwrite(optimized_path, resized)
    return optimized_path

def get_cache_key(audio_path, image_path):
    """Generate a unique cache key based on input files"""
    # Get file modification times
    audio_mtime = os.path.getmtime(audio_path)
    image_mtime = os.path.getmtime(image_path)
    
    # Create a unique key
    key = f"{audio_path}_{image_path}_{audio_mtime}_{image_mtime}"
    return hashlib.md5(key.encode()).hexdigest()

def check_cache(cache_key):
    """Check if we have a cached result"""
    cache_dir = Path('temp/cache')
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if cache_file.exists():
        return str(cache_file)
    return None

def save_to_cache(cache_key, video_path):
    """Save the generated video to cache"""
    cache_dir = Path('temp/cache')
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if os.path.exists(video_path):
        os.rename(video_path, str(cache_file))
        return str(cache_file)
    return None

def run_wav2lip(video_path, audio_path, output_path):
    """Run the Wav2Lip model on the video and audio"""
    print(f"Debug: Starting Wav2Lip with image: library/avatar.jpeg")
    if not os.path.exists("library/avatar.jpeg"):
        raise FileNotFoundError(f"Input image file not found: library/avatar.jpeg")
    
    # Check cache first
    cache_key = get_cache_key(audio_path, "library/avatar.jpeg")
    cached_video = check_cache(cache_key)
    if cached_video:
        print("Debug: Using cached video")
        return cached_video
    
    # Optimize input image resolution
    optimized_image = optimize_image_resolution("library/avatar.jpeg")
    
    wav2lip_dir = os.path.join(os.path.dirname(__file__), 'Wav2Lip')
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    
    # Check if CUDA is available
    import torch
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Debug: Using device: {device}")
    
    # Optimize batch sizes based on device
    face_det_batch_size = 4 if device == 'cuda' else 1
    wav2lip_batch_size = 4 if device == 'cuda' else 1
    
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
    
    print(f"Debug: Running Wav2Lip command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running Wav2Lip: {result.stderr}")
            raise RuntimeError(f"Wav2Lip failed with error: {result.stderr}")
    except Exception as e:
        print(f"Error during Wav2Lip execution: {str(e)}")
        raise
    
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Wav2Lip failed to generate output video: {output_path}")
    
    # Save to cache
    cached_path = save_to_cache(cache_key, output_path)
    if cached_path:
        print("Debug: Video saved to cache")
        return cached_path
    
    print("Debug: Wav2Lip completed successfully")
    return output_path

def play_audio_and_video(video_path, audio_path):
    """Play the generated video with audio"""
    print("Debug: Starting audio/video playback")
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return
        
    try:
        print("Debug: Loading audio file")
        # Load audio file
        audio_data, sample_rate = sf.read(audio_path)
        
        print("Debug: Starting audio playback")
        # Start audio playback
        sd.play(audio_data, sample_rate)
        
        print("Debug: Opening video file")
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Could not open video.")
            return
        
        # Get video properties
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print("Debug: Creating window")
        # Create window
        window_name = "AI Assistant Video"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, frame_width, frame_height)
        
        # Calculate frame delay
        frame_delay = int(1000/fps)
        
        print("Debug: Starting video playback loop")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            cv2.imshow(window_name, frame)
            
            # Break on 'q' press or window close
            if cv2.waitKey(frame_delay) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"Error during playback: {str(e)}")
    finally:
        print("Debug: Cleaning up resources")
        # Clean up
        sd.stop()
        if 'cap' in locals():
            cap.release()
        cv2.destroyAllWindows()
        print("Debug: Cleanup complete")

def main():
    print("🎥 AI Assistant with Lip Sync")
    print("Speak when prompted. Type 'exit' to quit.")
    print("Press 'q' to close the video window when playing.\n")
    
    ensure_directories()
    
    # Check if idle_video.mp4 exists
    input_video = os.path.join('library', 'idle_video.mp4')
    if not os.path.exists(input_video):
        print(f"Error: {input_video} not found. Please place the video file in the library directory.")
        return
    
    while True:
        print("Debug: Starting recording")
        # Step 1: Record and transcribe user input
        audio_file = record_audio()
        user_input = transcribe_audio(audio_file)
        print(f"\n🗣️ You said: {user_input}")

        # Exit condition
        if user_input.strip().lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        print("Debug: Getting assistant reply")
        # Step 2: Get assistant reply from Kirk logic module
        reply = get_kirk_text(user_input, chat_history)
        print(f"\n🤖 Assistant: {reply}\n")

        print("Debug: Generating speech")
        # Step 3: Generate speech using ElevenLabs (but don't play it yet)
        audio_output_path = speak_text_with_elevenlabs(reply, play_audio=False)

        # Step 4: Run Wav2Lip to generate lip-synced video
        output_video = "temp/response.mp4"
        
        print("🎬 Generating lip-synced video...")
        try:
            video_path = run_wav2lip(input_video, audio_output_path, output_video)
            print("✨ Video generated! Playing now...")
            
            # Step 5: Play the video with synchronized audio
            play_audio_and_video(video_path, audio_output_path)
        except Exception as e:
            print(f"Error during video generation: {str(e)}")

        # Step 6: Add to chat history
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    main() 