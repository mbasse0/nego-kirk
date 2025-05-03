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

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')

# Create audio directory if it doesn't exist
audio_dir = os.path.join(script_dir, 'audio')
os.makedirs(audio_dir, exist_ok=True)

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