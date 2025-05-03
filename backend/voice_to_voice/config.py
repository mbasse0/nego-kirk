# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the backend directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
env_path = os.path.join(backend_dir, '.env')

if os.path.exists(env_path):
    print(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")

# ─── API KEYS ─────────────────────────────────────────────────────────────
# Get API keys from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVEN_LABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')  # Note the name difference
ELEVEN_LABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', "5ERbh3mpIEzi6sfFHo7H")

# Check if the keys are set in environment variables
if not OPENAI_API_KEY:
    # If not in environment, try hardcoded values (not recommended for production)
    OPENAI_API_KEY = "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"
    print("⚠️ Using hardcoded OPENAI_API_KEY (not recommended for production)")

if not ELEVEN_LABS_API_KEY:
    # If not in environment, try hardcoded values (not recommended for production)
    ELEVEN_LABS_API_KEY = "sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"
    print("⚠️ Using hardcoded ELEVEN_LABS_API_KEY (not recommended for production)")

# ─── CHATBOT BEHAVIOR ──────────────────────────────────────────────────────────
# This will be the very first "system" prompt your assistant sees.
SYSTEM_PROMPT = (
    "You are Kirk Kinnell, a wise, calm, and strategic negotiation coach from Scotland. "
    "You speak with empathy and humor, drawing from law enforcement and high-stakes negotiations. "
    "You help users de-escalate conflict, reframe problems, and think ethically. "
    "Focus on relational integrity and practical strategies. Always maintain psychological safety. "
    "Use negotiation psychology, reframing, and emotional awareness in your replies."
    "You make short answers, only a few sentences long"
)

ENABLE_SPEECH = True  # Set to False if you want text-only responses

# ─── WHISPER MODEL ─────────────────────────────────────────────────────────────
WHISPER_MODEL = "whisper-1"  # or another OpenAI audio model
