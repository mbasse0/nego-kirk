import os
import openai
import concurrent.futures
from dotenv import load_dotenv
from whisper.op_kirk_agent import (
    get_kirk_response,
    summarize_reply,
    select_best_rag_chunk,
)
from whisper.rag_engine import retrieve_chunks

# Load environment and API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

chat_history = []


def main():
    print("💬 Kirk Text Chatbot (Type your questions)")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("🧑 You: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        # Step 1: Retrieve relevant book content
        rag_candidates = retrieve_chunks(user_input, k=3)

        # Step 2: Run LLM tasks in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_reply = executor.submit(get_kirk_response, user_input, chat_history)
            future_summary = executor.submit(
                lambda: summarize_reply(future_reply.result())
            )
            future_rag = executor.submit(
                lambda: select_best_rag_chunk(
                    rag_candidates, future_reply.result(), user_input
                )
            )

            reply = future_reply.result()
            summary = future_summary.result()
            rag_comment = future_rag.result()

        # Step 3: Update chat history
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": reply})

        # Step 4: Print results
        print(f"\n🤖 Kirk:\n{reply}\n")
        print(f"🧭 Summary:\n{summary}\n")
        print(f"📘 Book Insight:\n{rag_comment}\n")


if __name__ == "__main__":
    main()
