# config.py

# ─── YOUR API KEYS ─────────────────────────────────────────────────────────────
# (replace the placeholders with your real keys)
OPENAI_API_KEY = ""
ELEVEN_LABS_API_KEY = ""

# ─── VOICE SETTINGS ────────────────────────────────────────────────────────────
# The Eleven Labs voice you’ve cloned/selected
ELEVEN_LABS_VOICE_ID = "5ERbh3mpIEzi6sfFHo7H"

# ─── CHATBOT BEHAVIOR ──────────────────────────────────────────────────────────
# This will be the very first “system” prompt your assistant sees.
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
