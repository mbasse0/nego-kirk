# kirk_agent.py

from openai import OpenAI
from config import OPENAI_API_KEY, SYSTEM_PROMPT

client = OpenAI(api_key=OPENAI_API_KEY)


def get_kirk_text(user_input: str, chat_history: list[dict]) -> str:
    """
    Generate a Kirk-style assistant reply based on user input and chat history.
    Injects SYSTEM_PROMPT if not already included.
    """

    # Ensure the chat starts with Kirk's persona prompt
    if not any(m["role"] == "system" for m in chat_history):
        chat_history = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history

    # Add current user message
    messages = chat_history + [{"role": "user", "content": user_input}]

    # Query GPT
    try:
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        
        # Extract the response text
        reply = response.choices[0].message.content
        
        return reply
    except Exception as e:
        return f"❌ Error getting response from Kirk: {str(e)}"
