# main_voice2text.py

import openai
from speech_to_text import record_audio, transcribe_audio
from advisor import speak_text_with_elevenlabs
from kirk_agent import get_kirk_text  # ✅ NEW IMPORT
from config import OPENAI_API_KEY, SYSTEM_PROMPT, ENABLE_SPEECH

openai.api_key = OPENAI_API_KEY

# Initialize conversation
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]


def main():
    print("🎤 Voice Chatbot (Speak to type)")
    print("Speak when prompted. Type 'exit' to quit.\n")

    while True:
        # Step 1: Record and transcribe
        filename = record_audio()
        user_input = transcribe_audio(filename)
        print(f"\n🗣️ You said: {user_input}")

        # Exit condition
        if user_input.strip().lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        # Step 2: Get assistant reply from Kirk logic module
        reply = get_kirk_text(user_input, chat_history)
        print(f"\n🤖 Assistant: {reply}\n")

        # Step 3: Add to history
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": reply})

        # Step 4: Speak if enabled
        if ENABLE_SPEECH:
            speak_text_with_elevenlabs(reply)


if __name__ == "__main__":
    main()
