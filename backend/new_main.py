import os
import sys
import cv2
import subprocess
import hashlib
import uuid
import json
from pathlib import Path
import time
import shutil
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

# Add voice_to_voice directory to Python path
voice_to_voice_path = os.path.join(os.path.dirname(__file__), 'voice_to_voice')
sys.path.append(voice_to_voice_path)

# Import from voice_to_voice directory
from voice_to_voice.advisor import speak_text_with_elevenlabs
from voice_to_voice.kirk_agent import get_kirk_text
from voice_to_voice.config import SYSTEM_PROMPT

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Create necessary directories
def ensure_directories():
    """Create necessary directories if they don't exist"""
    print("Creating necessary directories...")
    dirs = ['temp', 'library', 'audio', 'output', 'temp/cache']
    for dir_name in dirs:
        dir_path = os.path.join(script_dir, dir_name)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    print("Directories created")

# Create directory paths
audio_dir = os.path.join(script_dir, 'audio')
video_dir = os.path.join(script_dir, 'output')
library_dir = os.path.join(script_dir, 'library')
temp_dir = os.path.join(script_dir, 'temp')

# Ensure directories exist
ensure_directories()

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize conversation history
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

class SpeechRequest(BaseModel):
    text: str

# ---------------------- COMBINED PIPELINE FUNCTIONS ----------------------

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
    cache_dir = Path(os.path.join(temp_dir, 'cache'))
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if cache_file.exists():
        return str(cache_file)
    return None

def save_to_cache(cache_key, video_path):
    """Save the generated video to cache"""
    cache_dir = Path(os.path.join(temp_dir, 'cache'))
    cache_dir.mkdir(exist_ok=True)
    
    cache_file = cache_dir / f"{cache_key}.mp4"
    if os.path.exists(video_path):
        # Copy instead of rename to preserve the original
        shutil.copy2(video_path, str(cache_file))
        return str(cache_file)
    return None

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
    
    # Check cache first
    cache_key = get_cache_key(audio_path, avatar_path)
    cached_video = check_cache(cache_key)
    if cached_video:
        print(f"Using cached video: {cached_video}")
        # Copy to output location
        shutil.copy2(cached_video, output_path)
        return output_path
    
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
    
    # Check if CUDA is available
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
            # Try fallback with explicit conda env
            try:
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
                    raise RuntimeError(f"Conda run also failed: {result.stderr}")
            except Exception as e:
                print(f"Conda fallback failed: {str(e)}")
                raise RuntimeError(f"Wav2Lip failed with error: {result.stderr}")
    except Exception as e:
        print(f"Error during Wav2Lip execution: {str(e)}")
        # Fall back to creating a static video
        return create_fallback_video(avatar_path, audio_path, output_path)
    
    # Check if the output file was created
    if not os.path.exists(output_path):
        print(f"Wav2Lip failed to generate output video: {output_path}")
        # Fall back to creating a static video
        return create_fallback_video(avatar_path, audio_path, output_path)
    
    # Save to cache
    cached_path = save_to_cache(cache_key, output_path)
    if cached_path:
        print(f"Video saved to cache: {cached_path}")
    
    print(f"Wav2Lip completed successfully: {output_path}")
    return output_path

def create_fallback_video(image_path, audio_path, output_path):
    """Create a simple video with the image and audio using ffmpeg"""
    print("Creating fallback video with ffmpeg")
    
    # Check if ffmpeg is available
    try:
        subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=True
        )
        print("FFmpeg is available")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("ffmpeg is not installed or not available in PATH")
        raise RuntimeError("FFmpeg not available for fallback video generation")
    
    # Get audio duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    duration = float(result.stdout.strip())
    print(f"Audio duration: {duration} seconds")
    
    # Create video from image and audio
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", str(duration),
        output_path
    ]
    
    print(f"Running FFmpeg command: {' '.join(command)}")
    subprocess.run(command, check=True)
    
    # Verify the video was created
    if not os.path.exists(output_path):
        raise FileNotFoundError(f"Failed to generate output video: {output_path}")
        
    print(f"Fallback video created at {output_path}")
    return output_path

# ---------------------- API ENDPOINTS ----------------------

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        print("Received audio file for transcription")
        
        # Save uploaded file
        audio_filename = f"{uuid.uuid4()}.wav"
        audio_filepath = os.path.join(audio_dir, audio_filename)
        
        with open(audio_filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Import here to avoid circular imports
        from voice_to_voice.speech_to_text import transcribe_audio as whisper_transcribe
        
        # Transcribe audio
        transcript = whisper_transcribe(audio_filepath)
        print(f"Transcription successful: {transcript}")
        
        return {"text": transcript}
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-speech")
async def generate_speech(request: SpeechRequest):
    try:
        print(f"Generating speech for text: {request.text}")
        
        # Get Kirk's response using GPT
        chat_history.append({"role": "user", "content": request.text})
        kirk_response = get_kirk_text(request.text, chat_history)
        chat_history.append({"role": "assistant", "content": kirk_response})
        
        # Generate speech using ElevenLabs
        audio_filepath = speak_text_with_elevenlabs(kirk_response, play_audio=False)
        
        if not audio_filepath:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Get just the filename from the filepath
        audio_filename = os.path.basename(audio_filepath)
        
        return {
            "audio_url": f"/audio/{audio_filename}",
            "text": kirk_response
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-video")
async def generate_video(request: SpeechRequest):
    try:
        print(f"Generating video for text: {request.text}")
        
        # Get Kirk's response using GPT
        chat_history.append({"role": "user", "content": request.text})
        kirk_response = get_kirk_text(request.text, chat_history)
        chat_history.append({"role": "assistant", "content": kirk_response})
        
        # Generate speech using ElevenLabs
        audio_filepath = speak_text_with_elevenlabs(kirk_response, play_audio=False)
        
        if not audio_filepath:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Get just the filename from the filepath
        audio_filename = os.path.basename(audio_filepath)
        
        # Generate video with lip-sync
        try:
            # Check for avatar
            avatar_path = os.path.join(library_dir, "avatar.jpeg")
            if not os.path.exists(avatar_path):
                # Try .png as fallback
                avatar_path = os.path.join(library_dir, "avatar.png")
                if not os.path.exists(avatar_path):
                    print("No avatar found, will use default in run_wav2lip")
                    avatar_path = None
            
            # Generate unique video filename
            video_filename = f"kirk_response_{uuid.uuid4()}.mp4"
            video_filepath = os.path.join(video_dir, video_filename)
            
            # Generate video using the combined_pipeline's function
            print("Generating lip-sync video...")
            output_path = run_wav2lip(
                audio_path=audio_filepath,
                output_path=video_filepath,
                avatar_path=avatar_path
            )
            
            if not os.path.exists(output_path):
                raise HTTPException(status_code=500, detail="Video generation failed")
            
            print(f"Video generated successfully at: {output_path}")
            
            # Return paths for both audio and video
            return {
                "audio_url": f"/audio/{audio_filename}",
                "video_url": f"/video/{video_filename}",
                "text": kirk_response
            }
            
        except Exception as e:
            print(f"Error during video generation: {str(e)}")
            # Return audio-only response if video generation fails
            return {
                "audio_url": f"/audio/{audio_filename}",
                "text": kirk_response,
                "error": f"Video generation failed: {str(e)}"
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    try:
        # Get the full path of the audio file
        audio_path = os.path.join(audio_dir, filename)
        
        # Check if file exists
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Return the audio file
        return FileResponse(audio_path, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video/{filename}")
async def get_video(filename: str):
    try:
        print(f"Requested video file: {filename}")
        
        # Get the full path of the video file
        video_path = os.path.join(video_dir, filename)
        
        # Check if file exists
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")
        
        print(f"Serving video from {video_path}, size: {os.path.getsize(video_path)} bytes")
        return FileResponse(
            path=video_path, 
            media_type="video/mp4",
            filename=filename
        )
    except Exception as e:
        print(f"Error serving video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    try:
        # Save avatar to library directory with both extensions
        avatar_jpeg_path = os.path.join(library_dir, "avatar.jpeg")
        avatar_png_path = os.path.join(library_dir, "avatar.png")
        
        # Read and save file
        content = await file.read()
        with open(avatar_jpeg_path, 'wb') as f:
            f.write(content)
        
        # Also save as PNG for compatibility
        with open(avatar_png_path, 'wb') as f:
            f.write(content)
        
        return {"message": "Avatar uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-video")
async def test_video():
    """Test endpoint to serve a test video directly"""
    try:
        # Check for avatar
        avatar_path = os.path.join(library_dir, "avatar.jpeg")
        if not os.path.exists(avatar_path):
            avatar_path = os.path.join(library_dir, "avatar.png")
            if not os.path.exists(avatar_path):
                raise HTTPException(status_code=404, detail="No avatar found")
        
        # Generate a test audio
        test_text = "This is a test of the lip sync system."
        audio_filepath = speak_text_with_elevenlabs(test_text, play_audio=False)
        
        # Generate unique video filename
        video_filename = f"test_video_{uuid.uuid4()}.mp4"
        video_filepath = os.path.join(video_dir, video_filename)
        
        # Generate test video
        output_path = run_wav2lip(
            audio_path=audio_filepath,
            output_path=video_filepath,
            avatar_path=avatar_path
        )
        
        # Return video path
        return {
            "video_url": f"/video/{os.path.basename(output_path)}",
            "text": test_text
        }
    except Exception as e:
        print(f"Error generating test video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Ensure directories exist
    ensure_directories()
    # Start server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 