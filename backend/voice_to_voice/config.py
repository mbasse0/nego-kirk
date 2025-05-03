# config.py

# ─── YOUR API KEYS ─────────────────────────────────────────────────────────────
# (replace the placeholders with your real keys)
OPENAI_API_KEY = "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"
ELEVEN_LABS_API_KEY = "sk_0b7a6164f585943ca034e1faf6f15ac3e3dbe58b8bc1f5bb"

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
