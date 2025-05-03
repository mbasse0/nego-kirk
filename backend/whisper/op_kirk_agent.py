from openai import OpenAI
import os
from dotenv import load_dotenv

# from config import COACH_SYSTEM_PROMPT, NEGOTIATOR_SYSTEM_PROMPT
from whisper.config import COACH_SYSTEM_PROMPT, NEGOTIATOR_SYSTEM_PROMPT

# Load keys
load_dotenv()
# Initialize OpenAI client without proxies parameter
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


def classify_role(user_input: str) -> str:
    """
    Use GPT to classify the user's intent on this turn: coaching vs negotiator.
    """
    prompt = f"""
You are an intent classification assistant.

Your job is to determine whether the user is:
- Asking for negotiation **coaching** (tips, feedback, guidance, theory), or
- Engaging in a **live negotiation** (role-play, simulation, real interaction)

The user message is:

"{user_input}"

Respond with exactly one word:
- "coaching" if they are asking for training, or explanation
- "negotiator" if they are asking you to negotiate for them, simulate a negotiation or help them in a live negotiation
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip().lower()


def get_kirk_response(user_input: str, chat_history: list[dict]) -> str:
    """
    Classify role, build prompt with persona, and return Kirk's assistant reply.
    """
    role = classify_role(user_input)
    print(f"[Router → Role selected: {role}]")

    # Load persona
    try:
        with open("persona.txt", "r", encoding="utf-8") as f:
            persona_text = f.read().strip()
    except FileNotFoundError:
        persona_text = ""

    base_prompt = (
        COACH_SYSTEM_PROMPT if role == "coaching" else NEGOTIATOR_SYSTEM_PROMPT
    )
    full_prompt = f"{persona_text}\n\n{base_prompt}" if persona_text else base_prompt

    messages = [{"role": "system", "content": full_prompt}]
    messages += chat_history + [{"role": "user", "content": user_input}]

    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def summarize_reply(reply: str) -> str:
    """
    Bullet-point summary for display. Outputs 2–5 key points.
    """
    prompt = f"""
Summarize the assistant's reply into a bullet list of the key ideas.
Use 2 to 5 bullet points. Be concise.

Reply:
{reply}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def select_best_rag_chunk(
    rag_chunks: list[dict], kirk_reply: str, user_query: str
) -> str:
    """
    From top-3 RAG chunks, select the most relevant one based on Kirk's reply and user query.
    If none are clearly helpful, return a fallback message.
    """
    if not rag_chunks or not kirk_reply:
        return "No relevant content from the book."

    numbered_chunks = "\n\n".join(
        f"{i + 1}. Page {chunk['page']}:\n{chunk['text']}"
        for i, chunk in enumerate(rag_chunks)
    )

    prompt = f"""
You are helping match Kirk's reply with content from his book.
Here is the user query:
"{user_query}"

Here are three short excerpts from his book:

{numbered_chunks}

Instructions:
- Decide whether any of these excerpts are relevant to the user query.
- If none are clearly helpful AND related, respond with exactly:
No relevant content from the book.
- Otherwise, if one of the excerpts contains several words or ideas Kirk expressed in his reply, choose the **most relevant** one if it clearly supports or explains Kirk's reply.

If one is relevant, return it in the format:
Here's what I say in my book on page X: ... (followed by the cleaned excerpt)
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    output = response.choices[0].message.content.strip()

    if "no relevant content" in output.lower():
        return "No relevant content from the book."
    return output
