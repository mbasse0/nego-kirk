import os
import requests
import pygame
import time
from config import ELEVEN_LABS_API_KEY, ELEVEN_LABS_VOICE_ID


def speak_text_with_elevenlabs(text, play_audio=True):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_LABS_VOICE_ID}/stream"

    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.2,
            "similarity_boost": 0.95,
            "style": 0.5,
            "use_speaker_boost": True,
        },
    }
    headers = {"xi-api-key": ELEVEN_LABS_API_KEY}

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print("🔴 Failed to generate speech:", response.text)
        return

    filename = "reply.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)

    if play_audio:
        print(f"🔊 Playing: {filename}")
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            time.sleep(0.1)  # Wait a bit before checking

            # Wait until audio is done
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print("❌ Error during playback:", e)
    
    return filename
