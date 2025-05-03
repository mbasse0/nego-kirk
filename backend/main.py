from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import os
import tempfile
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from openai import OpenAI
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import requests
import json
import cv2
import subprocess
import time
import shutil
import glob
import sys
from pathlib import Path
from whisper.op_kirk_agent import (
    get_kirk_response,
    summarize_reply,
    select_best_rag_chunk,
)
from whisper.rag_engine import retrieve_chunks


# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")

# Create necessary directories
audio_dir = os.path.join(script_dir, "audio")
video_dir = os.path.join(script_dir, "video")
library_dir = os.path.join(script_dir, "library")
temp_dir = os.path.join(script_dir, "temp")

for dir_path in [audio_dir, video_dir, library_dir, temp_dir]:
    os.makedirs(dir_path, exist_ok=True)

# Create temporary working directory with no spaces
temp_working_dir = "/tmp/wav2lip_temp"
os.makedirs(temp_working_dir, exist_ok=True)

# Load environment variables
load_dotenv(env_path)

# Debug environment variables
print("Environment Variables:")
print(f"Current working directory: {os.getcwd()}")
print(f"Script directory: {script_dir}")
print(f"Audio directory: {audio_dir}")
print(f"Env file path: {env_path}")
print(f"Env file exists: {os.path.exists(env_path)}")
print(f"ELEVENLABS_API_KEY exists: {'ELEVENLABS_API_KEY' in os.environ}")
print(f"OPENAI_API_KEY exists: {'OPENAI_API_KEY' in os.environ}")

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

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt for Kirk
SYSTEM_PROMPT = (
    "You are Kirk Kinnell, a wise, calm, and strategic negotiation coach from Scotland. "
    "You speak with empathy and humor, drawing from law enforcement and high-stakes negotiations. "
    "You help users de-escalate conflict, reframe problems, and think ethically. "
    "Focus on relational integrity and practical strategies. Always maintain psychological safety. "
    "Use negotiation psychology, reframing, and emotional awareness in your replies."
    "You make short answers, only a few sentences long"
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
    
    # Optimize image resolution (higher resolution for better quality)
    img = cv2.imread(avatar_path)
    height, width = img.shape[:2]
    aspect_ratio = width / height
    
    # Using 512px width for higher quality (up from 256)
    new_width = 512
    new_height = int(new_width / aspect_ratio)
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Save as PNG for higher quality
    optimized_image = os.path.join(temp_dir, 'optimized_avatar.png')
    cv2.imwrite(optimized_image, resized, [cv2.IMWRITE_PNG_COMPRESSION, 0])
    
    # Find Wav2Lip directory (case insensitive)
    if os.path.exists(os.path.join(script_dir, 'wav2lip')):
        wav2lip_dir = os.path.join(script_dir, 'wav2lip')
    elif os.path.exists(os.path.join(script_dir, 'Wav2Lip')):
        wav2lip_dir = os.path.join(script_dir, 'Wav2Lip')
    else:
        raise FileNotFoundError("Wav2Lip directory not found")
    
    # Copy files to the temporary directory
    temp_audio = os.path.join(temp_working_dir, f"input_{unique_id}.mp3")
    temp_image = os.path.join(temp_working_dir, f"face_{unique_id}.png")
    temp_output = os.path.join(temp_working_dir, f"output_{unique_id}.mp4")
    
    shutil.copy2(audio_path, temp_audio)
    shutil.copy2(optimized_image, temp_image)
    
    # Set paths
    inference_path = os.path.join(wav2lip_dir, 'inference.py')
    checkpoint_path = os.path.join(wav2lip_dir, 'checkpoints', 'wav2lip_gan.pth')
    
    # Check if we need to convert from AVI to MP4
    temp_avi_path = os.path.join('temp', 'result.avi')
    temp_mp4_path = os.path.join('temp', 'result.mp4')
    
    # Improved command for Wav2Lip with better padding
    # Removed --nosmooth for better temporal consistency
    command = [
        'python', inference_path,
        '--checkpoint_path', checkpoint_path,
        '--face', temp_image,
        '--audio', temp_audio,
        '--outfile', temp_output,
        '--pads', '0', '10', '0', '0',  # Increased bottom padding
        '--fps', '30'  # Higher frame rate for smoother video
    ]
    
    # Run Wav2Lip
    print("Running Wav2Lip...")
    try:
        subprocess.run(command, check=True)
        
        # Check if we need to convert AVI to MP4 (if temp/result.avi exists but not MP4)
        if os.path.exists(temp_avi_path) and not os.path.exists(temp_mp4_path):
            print("Converting AVI to MP4 with higher quality...")
            convert_command = [
                'ffmpeg', '-y', '-i', temp_avi_path, 
                '-c:v', 'libx264', '-preset', 'slow',  # Slower preset for better quality
                '-crf', '18',  # Lower CRF value means higher quality (18 is high quality)
                '-c:a', 'aac', '-b:a', '320k',  # Higher audio bitrate
                '-pix_fmt', 'yuv420p', 
                '-maxrate', '8M', '-bufsize', '16M',  # Higher bitrate for better quality
                temp_mp4_path
            ]
            subprocess.run(convert_command, check=True)
            
            # Use the MP4 file for the output
            if os.path.exists(temp_mp4_path):
                shutil.copy2(temp_mp4_path, output_path)
                print(f"Success! High-quality MP4 output saved to: {output_path}")
                return os.path.basename(output_path)
        
        # If direct output exists, also apply high-quality conversion
        if os.path.exists(temp_output):
            print("Enhancing output video quality...")
            enhanced_output = os.path.join(temp_working_dir, f"enhanced_{unique_id}.mp4")
            enhance_command = [
                'ffmpeg', '-y', '-i', temp_output, 
                '-c:v', 'libx264', '-preset', 'slow',  # Slower preset for better quality
                '-crf', '18',  # Lower CRF value means higher quality
                '-c:a', 'aac', '-b:a', '320k',  # Higher audio bitrate
                '-pix_fmt', 'yuv420p',
                '-maxrate', '8M', '-bufsize', '16M',  # Higher bitrate for better quality
                enhanced_output
            ]
            subprocess.run(enhance_command, check=True)
            
            # Use the enhanced output if it exists
            if os.path.exists(enhanced_output):
                shutil.copy2(enhanced_output, output_path)
                print(f"Success! Enhanced output saved to: {output_path}")
                return os.path.basename(output_path)
            
            # Otherwise use the original output
            shutil.copy2(temp_output, output_path)
            print(f"Success! Output saved to: {output_path}")
            return os.path.basename(output_path)
        else:
            print("Failed to generate video.")
            return None
    except Exception as e:
        print(f"Error running Wav2Lip: {str(e)}")
        return None


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        print("Received audio file for transcription")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            print(f"Saved audio to temporary file: {temp_file_path}")

        try:
            # Transcribe audio using OpenAI's Whisper API
            with open(temp_file_path, "rb") as audio_file:
                print("Sending audio to Whisper API")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, language="en"
                )
                print(f"Transcription successful: {transcript.text}")

                # Clean up temporary file
                os.unlink(temp_file_path)

                return {"text": transcript.text}
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            # Clean up temporary file in case of error
            os.unlink(temp_file_path)
            raise HTTPException(
                status_code=500, detail=f"Transcription failed: {str(e)}"
            )

    except Exception as e:
        print(f"Error processing audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-speech")
async def generate_speech(request: SpeechRequest):
    try:
        print(f"Generating speech for text: {request.text}")

        # Get Kirk's response using GPT
        # chat_history.append({"role": "user", "content": request.text})
        # response = client.chat.completions.create(
        #     model="gpt-3.5-turbo", messages=chat_history
        # )
        # kirk_response = response.choices[0].message.content
        # chat_history.append({"role": "assistant", "content": kirk_response})
        rag_chunks = retrieve_chunks(request.text, k=3)
        kirk_response = get_kirk_response(request.text, chat_history)
        summary = summarize_reply(kirk_response)
        book_insight = select_best_rag_chunk(rag_chunks, kirk_response, request.text)
        chat_history.append({"role": "user", "content": request.text})
        chat_history.append({"role": "assistant", "content": kirk_response})

        # Generate speech using ElevenLabs
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "5ERbh3mpIEzi6sfFHo7H")

        if not elevenlabs_api_key:
            raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not set")

        url = (
            f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}/stream"
        )
        payload = {
            "text": kirk_response,
            "voice_settings": {
                "stability": 0.2,
                "similarity_boost": 0.95,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }
        headers = {"xi-api-key": elevenlabs_api_key}

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail=f"Error generating speech: {response.text}"
            )

        # Save audio to file in audio directory
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"Audio saved to: {filepath}")

        # return {"audio_url": f"/audio/{filename}", "text": kirk_response}
        return {
            "audio_url": f"/audio/{filename}",
            "text": kirk_response,
            "summary": summary,
            "book_insight": book_insight,
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-video")
async def generate_video(request: SpeechRequest):
    try:
        print(f"Generating video for text: {request.text}")
        
        # Get Kirk's response using GPT with RAG
        rag_chunks = retrieve_chunks(request.text, k=3)
        kirk_response = get_kirk_response(request.text, chat_history)
        summary = summarize_reply(kirk_response)
        book_insight = select_best_rag_chunk(rag_chunks, kirk_response, request.text)
        chat_history.append({"role": "user", "content": request.text})
        chat_history.append({"role": "assistant", "content": kirk_response})
        
        # Generate speech using ElevenLabs
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "5ERbh3mpIEzi6sfFHo7H")
        
        if not elevenlabs_api_key:
            raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not set")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{elevenlabs_voice_id}/stream"
        payload = {
            "text": kirk_response,
            "voice_settings": {
                "stability": 0.2,
                "similarity_boost": 0.95,
                "style": 0.5,
                "use_speaker_boost": True,
            },
        }
        headers = {"xi-api-key": elevenlabs_api_key}
        
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Error generating speech: {response.text}")
        
        # Save audio to file in audio directory
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_filepath = os.path.join(audio_dir, audio_filename)
        with open(audio_filepath, "wb") as f:
            f.write(response.content)
        print(f"Audio saved to: {audio_filepath}")
        
        # Store the latest audio file for future use
        global latest_audio_file
        latest_audio_file = audio_filepath
        
        # Run Wav2Lip to generate video
        video_filename = run_wav2lip(audio_filepath)
        
        if video_filename:
            # Store the latest video file
            global latest_video_file
            latest_video_file = os.path.join(video_dir, video_filename)
            
            return {
                "audio_url": f"/audio/{audio_filename}",
                "video_url": f"/video/{video_filename}",
                "text": kirk_response,
                "summary": summary,
                "book_insight": book_insight
            }
        else:
            # Return audio-only response if video generation fails
            return {
                "audio_url": f"/audio/{audio_filename}",
                "text": kirk_response,
                "summary": summary,
                "book_insight": book_insight,
                "error": "Video generation failed"
            }
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video/idle_video.mp4")
async def get_idle_video():
    try:
        print("Requested idle video file")
        
        # Get the full path of the idle video file
        idle_video_path = os.path.join(library_dir, "idle_video.mp4")
        
        # Check if file exists
        if not os.path.exists(idle_video_path):
            raise HTTPException(status_code=404, detail="Idle video file not found")
        
        print(f"Serving idle video from {idle_video_path}, size: {os.path.getsize(idle_video_path)} bytes")
        return FileResponse(
            path=idle_video_path, 
            media_type="video/mp4",
            filename="idle_video.mp4"
        )
    except Exception as e:
        print(f"Error serving idle video: {str(e)}")
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
 