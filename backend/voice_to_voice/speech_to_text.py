# speech_to_text.py

import sounddevice as sd
from scipy.io.wavfile import write
from openai import OpenAI
import numpy as np
from config import OPENAI_API_KEY
import time

client = OpenAI(api_key=OPENAI_API_KEY)


def record_audio(filename="input.wav", fs=44100):
    print("🎙️ Press Enter to start recording...")
    input()  # Wait for Enter key
    print("🔴 Recording... Press Enter again to stop.")

    # Start recording
    recording = []
    stream = sd.InputStream(samplerate=fs, channels=1, dtype="int16")
    stream.start()

    # Record start time
    start_time = time.time()
    MIN_DURATION = 0.5  # Minimum duration in seconds

    # Create a separate thread to wait for input
    def wait_for_input():
        input()
        return True

    import threading
    stop_thread = threading.Thread(target=wait_for_input)
    stop_thread.daemon = True
    stop_thread.start()

    try:
        while stop_thread.is_alive() or (time.time() - start_time) < MIN_DURATION:
            frame, _ = stream.read(1024)
            recording.append(frame)
            time.sleep(0.001)  # Small delay to prevent high CPU usage
    except Exception as e:
        print(f"Error during recording: {str(e)}")
    finally:
        stream.stop()
        audio = np.concatenate(recording, axis=0)
        write(filename, fs, audio)
        duration = len(audio) / fs
        print(f"✅ Audio saved to {filename} (Duration: {duration:.2f} seconds)")
        return filename


def transcribe_audio(filename="input.wav", model="whisper-1"):
    with open(filename, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model=model,
            file=audio_file
        )
    return response.text
