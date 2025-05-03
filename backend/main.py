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
import video_generator

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')

# Create audio directory if it doesn't exist
audio_dir = os.path.join(script_dir, 'audio')
os.makedirs(audio_dir, exist_ok=True)

# Create output directory for videos
video_dir = os.path.join(script_dir, 'output')
os.makedirs(video_dir, exist_ok=True)

# Create library directory for avatar images
library_dir = os.path.join(script_dir, 'library')
os.makedirs(library_dir, exist_ok=True)

# Load environment variables
load_dotenv(env_path)

# Debug environment variables
print("Environment Variables:")
print(f"Current working directory: {os.getcwd()}")
print(f"Script directory: {script_dir}")
print(f"Audio directory: {audio_dir}")
print(f"Video directory: {video_dir}")
print(f"Library directory: {library_dir}")
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

class SpeechRequest(BaseModel):
    text: str

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
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
                print(f"Transcription successful: {transcript.text}")
                
                # Clean up temporary file
                os.unlink(temp_file_path)
                
                return {"text": transcript.text}
        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            # Clean up temporary file in case of error
            os.unlink(temp_file_path)
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
            
    except Exception as e:
        print(f"Error processing audio file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-speech")
async def generate_speech(request: SpeechRequest):
    try:
        print(f"Generating speech for text: {request.text}")
        
        # Get Kirk's response using GPT
        chat_history.append({"role": "user", "content": request.text})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history
        )
        kirk_response = response.choices[0].message.content
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
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(audio_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"Audio saved to: {filepath}")

        return {"audio_url": f"/audio/{filename}", "text": kirk_response}
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-video")
async def generate_video(request: SpeechRequest):
    try:
        print(f"Generating video for text: {request.text}")
        
        # Get Kirk's response using GPT
        chat_history.append({"role": "user", "content": request.text})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history
        )
        kirk_response = response.choices[0].message.content
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

        # Save audio to file
        audio_filename = f"{uuid.uuid4()}.mp3"
        audio_filepath = os.path.join(audio_dir, audio_filename)
        with open(audio_filepath, 'wb') as f:
            f.write(response.content)
        print(f"Audio saved to: {audio_filepath}")

        # Generate video using Wav2Lip
        try:
            # Check for avatar.jpeg first (to match combined_pipeline.py)
            avatar_path = os.path.join(library_dir, "avatar.jpeg")
            if not os.path.exists(avatar_path):
                # Try .png as fallback
                avatar_path = os.path.join(library_dir, "avatar.png")
                if not os.path.exists(avatar_path):
                    print("Avatar image not found, creating default")
                    # The generator will create a default avatar if needed

            # Generate unique video filename
            video_filename = f"kirk_response_{uuid.uuid4()}.mp4"
            video_filepath = os.path.join(video_dir, video_filename)

            # Generate video
            print("Generating lip-sync video...")
            video_generator.generate_video(
                audio_path=audio_filepath,
                output_path=video_filepath,
                avatar_path=avatar_path if os.path.exists(avatar_path) else None
            )

            if not os.path.exists(video_filepath):
                raise HTTPException(status_code=500, detail="Video generation failed")

            print(f"Video generated successfully at: {video_filepath}")
            
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
        
        # Get the base name without extension
        base_name = os.path.splitext(filename)[0]
        
        # First check for MP4 files (preferred)
        mp4_paths = [
            os.path.join("output", f"{base_name}.mp4"),
            os.path.join(video_dir, f"{base_name}.mp4"),
            os.path.join("output", filename) if filename.endswith('.mp4') else "",
            os.path.join(video_dir, filename) if filename.endswith('.mp4') else "",
            os.path.join("temp/cache", f"{base_name}.mp4"),
        ]
        mp4_paths = [p for p in mp4_paths if p]  # Remove empty strings
        
        # Then check for HTML files (fallback)
        html_paths = [
            os.path.join("output", f"{base_name}.html"),
            os.path.join(video_dir, f"{base_name}.html"),
            os.path.join("output", filename) if filename.endswith('.html') else "",
            os.path.join(video_dir, filename) if filename.endswith('.html') else "",
            os.path.join("temp/cache", f"{base_name}.html"),
        ]
        html_paths = [p for p in html_paths if p]  # Remove empty strings
        
        # Combine with MP4 priority
        all_paths = mp4_paths + html_paths
        
        # Print all paths we're checking
        print(f"Checking these paths for video:")
        for path in all_paths:
            exists = os.path.exists(path)
            size = os.path.getsize(path) if exists else 0
            print(f"  - {path} (exists: {exists}, size: {size} bytes)")
        
        # Find the first path that exists and is not empty
        video_path = next((path for path in all_paths if os.path.exists(path) and os.path.getsize(path) > 0), None)
        
        # Check if file exists
        if not video_path:
            print(f"Video file not found: {filename}")
            raise HTTPException(status_code=404, detail="Video file not found")
        
        print(f"Found video at: {video_path}")
        
        # Determine media type based on file extension
        extension = os.path.splitext(video_path)[1].lower()
        if extension == '.html':
            return FileResponse(video_path, media_type="text/html")
        else:
            print(f"Serving MP4 file from {video_path}, size: {os.path.getsize(video_path)} bytes")
            return FileResponse(
                path=video_path, 
                media_type="video/mp4",
                filename=os.path.basename(video_path)
            )
    except Exception as e:
        print(f"Error serving video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-avatar")
async def upload_avatar(file: UploadFile = File(...)):
    try:
        # Save avatar to library directory
        avatar_path = os.path.join(library_dir, "avatar.jpeg")
        
        # Read and save file
        content = await file.read()
        with open(avatar_path, 'wb') as f:
            f.write(content)
        
        return {"message": "Avatar uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-video")
async def test_video():
    """Test endpoint to serve the silence.mp4 file directly"""
    try:
        video_path = os.path.join("library", "silence.mp4")
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Test video file not found")
            
        print(f"Serving test video from {video_path}, size: {os.path.getsize(video_path)} bytes")
        return FileResponse(
            path=video_path, 
            media_type="video/mp4",
            filename="silence.mp4"
        )
    except Exception as e:
        print(f"Error serving test video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 