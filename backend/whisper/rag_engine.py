# rag_engine.py

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter

# from config import OPENAI_API_KEY
from whisper.config import OPENAI_API_KEY

import openai
import os

openai.api_key = OPENAI_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
import os


def load_and_index_pdf(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "Kirkbook.pdf")

    loader = PyPDFLoader(path)
    docs = loader.load()  # Each Document includes metadata["page"]
    splitter = CharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings()
    db = FAISS.from_documents(splits, embeddings)
    return db


VECTOR_DB = load_and_index_pdf()


def retrieve_chunks(query: str, k: int = 3, min_words: int = 30) -> list[dict]:
    """
    Retrieve top-k results only if they are more relevant to the query than to a generic phrase.
    Returns cleaned text and page.
    """
    baseline = "this is how I negotiate"
    comparison = VECTOR_DB.similarity_search_with_score(baseline, k=1)
    baseline_score = comparison[0][1] if comparison else 0.0

    results_with_score = VECTOR_DB.similarity_search_with_score(query, k=k)
    cleaned = []

    for doc, score in results_with_score:
        if score <= baseline_score:
            continue

        text = doc.page_content.strip()
        page = doc.metadata.get("page", "unknown")

        if not text or len(text.split()) < min_words:
            continue

        # Clean the text using GPT
        cleaning_prompt = f"""
Here is a noisy or partial paragraph from a negotiation manual:

{text}

Your job is to:
- Remove partial sentences at the beginning or end
- Make the paragraph grammatically clean and self-contained
- Keep it brief (3–5 sentences), no added commentary

Return only the cleaned paragraph.
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": cleaning_prompt}],
                temperature=0,
            )
            cleaned_text = response.choices[0].message.content.strip()

        except Exception as e:
            cleaned_text = text  # fallback to raw

        cleaned.append({"text": cleaned_text, "page": page})

    return cleaned
