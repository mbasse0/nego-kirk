import os
import sys
import cv2
import subprocess
import time
import shutil
import uuid
from pathlib import Path
import glob

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add voice_to_voice directory to Python path
voice_to_voice_path = os.path.join(os.path.dirname(__file__), 'voice_to_voice')
sys.path.append(voice_to_voice_path)

# Import from voice_to_voice directory
from voice_to_voice.advisor import speak_text_with_elevenlabs
from voice_to_voice.kirk_agent import get_kirk_text
from voice_to_voice.config import SYSTEM_PROMPT
from voice_to_voice.speech_to_text import transcribe_audio as whisper_transcribe

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Create directory paths
audio_dir = os.path.join(script_dir, 'audio')
video_dir = os.path.join(script_dir, 'output')
library_dir = os.path.join(script_dir, 'library')
temp_dir = os.path.join(script_dir, 'temp')
results_dir = os.path.join(script_dir, 'results')

# Create necessary directories
for dir_path in [audio_dir, video_dir, library_dir, temp_dir, results_dir]:
    os.makedirs(dir_path, exist_ok=True)

# Create temporary working directory with no spaces
temp_working_dir = "/tmp/wav2lip_temp"
os.makedirs(temp_working_dir, exist_ok=True)

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

# Track latest generated files
latest_audio_file = None
latest_video_file = None

class SpeechRequest(BaseModel):
    text: str

def run_wav2lip(audio_path, avatar_path=None):
    """Run the Wav2Lip model to generate a lip-synced video using the simplified approach"""
    print(f"Starting Wav2Lip with audio: {audio_path}")
    
    # Use the specified avatar or default
    if not avatar_path:
        avatar_path = os.path.join(library_dir, "avatar.jpeg")
        if not os.path.exists(avatar_path):
            # Try png as fallback
            avatar_path = os.path.join(library_dir, "avatar.png")
            if not os.path.exists(avatar_path):
                raise FileNotFoundError(f"No avatar found at {avatar_path}")
    
    # Generate unique output filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(video_dir, f"result_{timestamp}_{unique_id}.mp4")
    
    # Optimize image resolution
    img = cv2.imread(avatar_path)
    height, width = img.shape[:2]
    aspect_ratio = width / height
    new_height = int(256 / aspect_ratio)
    resized = cv2.resize(img, (256, new_height))
    optimized_image = os.path.join(temp_dir, 'optimized_avatar.jpeg')
    cv2.imwrite(optimized_image, resized)
    
    # Find Wav2Lip directory (case insensitive)
    if os.path.exists(os.path.join(script_dir, 'wav2lip')):
        wav2lip_dir = os.path.join(script_dir, 'wav2lip')
    elif os.path.exists(os.path.join(script_dir, 'Wav2Lip')):
        wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
    else:
        raise FileNotFoundError("Wav2Lip directory not found")
    
    # Copy files to the temporary directory
    temp_audio = os.path.join(temp_working_dir, f"input_{unique_id}.mp3")
    temp_image = os.path.join(temp_working_dir, f"face_{unique_id}.jpeg")
    temp_output = os.path.join(temp_working_dir, f"output_{unique_id}.mp4")
    
    shutil.copy2(audio_path, temp_audio)
    shutil.copy2(optimized_image, temp_image)
    
    # Set paths
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    
    # Check if we need to convert from AVI to MP4
    temp_avi_path = os.path.join('temp', 'result.avi')
    temp_mp4_path = os.path.join('temp', 'result.mp4')
    
    # Basic command with paths that don't have spaces
    command = [
        'python', inference_path,
        '--checkpoint_path', checkpoint_path,
        '--face', temp_image,
        '--audio', temp_audio,
        '--outfile', temp_output,
        '--pads', '0', '5', '0', '0',
        '--nosmooth'
    ]
    
    # Run Wav2Lip
    print("Running Wav2Lip...")
    try:
        subprocess.run(command, check=True)
        
        # Check if we need to convert AVI to MP4 (if temp/result.avi exists but not MP4)
        if os.path.exists(temp_avi_path) and not os.path.exists(temp_mp4_path):
            print("Converting AVI to MP4...")
            convert_command = [
                'ffmpeg', '-y', '-i', temp_avi_path, 
                '-c:v', 'libx264', '-preset', 'fast', 
                '-c:a', 'aac', '-b:a', '192k',
                '-pix_fmt', 'yuv420p', temp_mp4_path
            ]
            subprocess.run(convert_command, check=True)
            
            # Use the MP4 file for the output
            if os.path.exists(temp_mp4_path):
                shutil.copy2(temp_mp4_path, output_path)
                print(f"Success! MP4 output saved to: {output_path}")
                return os.path.basename(output_path)
        
        # Copy the result back if it exists
        if os.path.exists(temp_output):
            shutil.copy2(temp_output, output_path)
            print(f"Success! Output saved to: {output_path}")
            return os.path.basename(output_path)
        else:
            print("Failed to generate video.")
            return None
    except Exception as e:
        print(f"Error running Wav2Lip: {str(e)}")
        return None

def get_or_create_reply_file():
    """Find or create a reply.mp3 file in the audio directory"""
    reply_path = os.path.join(audio_dir, "reply.mp3")
    
    # If we have a recent audio file, use that
    global latest_audio_file
    if latest_audio_file and os.path.exists(latest_audio_file):
        shutil.copy2(latest_audio_file, reply_path)
        return reply_path
    
    # If reply.mp3 already exists, return it
    if os.path.exists(reply_path):
        return reply_path
    
    # Try to find the most recent mp3 file
    mp3_files = glob.glob(os.path.join(audio_dir, "*.mp3"))
    if mp3_files:
        newest_file = max(mp3_files, key=os.path.getctime)
        shutil.copy2(newest_file, reply_path)
        return reply_path
    
    return None

@app.post("/transcribe")
async def transcribe_uploaded_audio(file: UploadFile = File(...)):
    """Transcribe uploaded audio from microphone"""
    try:
        print("Received audio file for transcription")
        
        # Create unique filename
        filename = f"recording_{str(uuid.uuid4())[:8]}.wav"
        file_path = os.path.join(audio_dir, filename)
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Transcribe using Whisper
        transcript = whisper_transcribe(file_path)
        print(f"Transcription successful: {transcript}")
        
        # Return the transcription
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
        
        # Store the latest audio file for reply.mp3 endpoint
        global latest_audio_file
        latest_audio_file = audio_filepath
        
        # Also create reply.mp3 for compatibility
        reply_path = os.path.join(audio_dir, "reply.mp3")
        shutil.copy2(audio_filepath, reply_path)
        
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
        
        # Store the latest audio file for reply.mp3 endpoint
        global latest_audio_file
        latest_audio_file = audio_filepath
        
        # Also create reply.mp3 for compatibility
        reply_path = os.path.join(audio_dir, "reply.mp3")
        shutil.copy2(audio_filepath, reply_path)
        
        # Get just the filename from the filepath
        audio_filename = os.path.basename(audio_filepath)
        
        # Run simplified Wav2Lip
        video_filename = run_wav2lip(audio_filepath)
        
        if video_filename:
            # Store the latest video file
            global latest_video_file
            latest_video_file = os.path.join(video_dir, video_filename)
            
            return {
                "audio_url": f"/audio/{audio_filename}",
                "video_url": f"/video/{video_filename}",
                "text": kirk_response
            }
        else:
            # Return audio-only response if video generation fails
            return {
                "audio_url": f"/audio/{audio_filename}",
                "text": kirk_response,
                "error": "Video generation failed"
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/reply.mp3")
async def get_reply_audio():
    """Specialized endpoint for compatibility with old frontend"""
    try:
        print("Requesting /audio/reply.mp3")
        reply_path = get_or_create_reply_file()
        
        if not reply_path or not os.path.exists(reply_path):
            raise HTTPException(status_code=404, detail="No audio file available")
        
        print(f"Serving reply audio: {reply_path}")
        return FileResponse(reply_path, media_type="audio/mpeg")
    except Exception as e:
        print(f"Error serving reply.mp3: {str(e)}")
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
    """Test endpoint to generate a simple test video"""
    try:
        # Generate a test audio
        test_text = "This is a test of the lip sync system."
        audio_filepath = speak_text_with_elevenlabs(test_text, play_audio=False)
        
        if not audio_filepath:
            raise HTTPException(status_code=500, detail="Failed to generate test audio")
        
        # Store the latest audio file for reply.mp3 endpoint
        global latest_audio_file
        latest_audio_file = audio_filepath
        
        # Also create reply.mp3 for compatibility
        reply_path = os.path.join(audio_dir, "reply.mp3")
        shutil.copy2(audio_filepath, reply_path)
        
        # Run simplified Wav2Lip
        video_filename = run_wav2lip(audio_filepath)
        
        if not video_filename:
            raise HTTPException(status_code=500, detail="Failed to generate test video")
        
        # Store the latest video file
        global latest_video_file
        latest_video_file = os.path.join(video_dir, video_filename)
            
        return {
            "video_url": f"/video/{video_filename}",
            "text": test_text
        }
    except Exception as e:
        print(f"Error generating test video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug") 