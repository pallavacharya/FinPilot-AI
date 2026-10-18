
"""RAG pipeline for FinPilot AI document Q&A."""

import os
import re
from io import BytesIO
from pathlib import Path

import chromadb
import joblib
from dotenv import load_dotenv
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
import time
from google.genai import errors as genai_errors

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data" / "rag"
CHROMA_DIR = DATA_DIR / "chroma_db"
VECTORIZER_PATH = DATA_DIR / "tfidf_vectorizer.joblib"

COLLECTION_NAME = "finpilot_documents"
CHUNK_SIZE = 180
CHUNK_OVERLAP = 30
TOP_K = 4
MIN_SIMILARITY = 0.10

DATA_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BACKEND_DIR / ".env")

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_collection():
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _split_into_chunks(text: str) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    chunks = []

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + CHUNK_SIZE]).strip()
        if chunk:
            chunks.append(chunk)
        if start + CHUNK_SIZE >= len(words):
            break

    return chunks


def _read_pdf(content: bytes) -> list[dict]:
    """Extract text from each PDF page."""
    reader = PdfReader(BytesIO(content))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": page_number, "text": text})

    return pages


def _rebuild_index(new_records: list[dict]) -> int:
    """Rebuild the TF-IDF vectors and persistent Chroma collection."""
    existing = _get_collection()
    old_records = []

    if existing.count() > 0:
        stored = existing.get(include=["documents", "metadatas"])
        for text, metadata in zip(stored["documents"], stored["metadatas"]):
            old_records.append({
                "text": text,
                "filename": metadata["filename"],
                "page": metadata["page"],
            })
# Avoid retaining old copies of files being re-indexed.
    reindexed_filenames = {
        record["filename"] for record in new_records
    }

    old_records = [
        record
        for record in old_records
        if record["filename"] not in reindexed_filenames
    ]

    all_records = old_records + new_records

    if not all_records:
        return 0

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(
        [record["text"] for record in all_records]
    )

    chroma_client.delete_collection(COLLECTION_NAME)
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.add(
        ids=[f"chunk-{i}" for i in range(len(all_records))],
        documents=[record["text"] for record in all_records],
        metadatas=[
            {
                "filename": record["filename"],
                "page": int(record["page"]),
            }
            for record in all_records
        ],
        embeddings=matrix.toarray().astype(float).tolist(),
    )

    joblib.dump(vectorizer, VECTORIZER_PATH)
    return len(all_records)


def index_document(filename: str, content: bytes) -> dict:
    """Extract, chunk, vectorize and store an uploaded PDF."""
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF documents are supported currently.")

    if not content:
        raise ValueError("The uploaded document is empty.")

    pages = _read_pdf(content)
    new_records = []

    for page in pages:
        for chunk in _split_into_chunks(page["text"]):
            new_records.append({
                "text": chunk,
                "filename": Path(filename).name,
                "page": page["page"],
            })

    if not new_records:
        raise ValueError(
            "No extractable text found. Scanned PDFs may require OCR."
        )

    _rebuild_index(new_records)

    return {
        "filename": Path(filename).name,
        "status": "indexed",
        "chunks": len(new_records),
    }


def delete_document(filename: str) -> dict:
    """Remove an indexed document and rebuild the vector store."""
    clean_name = Path(filename).name
    existing = _get_collection()
    if existing.count() == 0:
        raise ValueError(f"Document '{clean_name}' not found.")

    stored = existing.get(include=["documents", "metadatas"])
    remaining = []
    found = False

    for text, metadata in zip(stored["documents"], stored["metadatas"]):
        if metadata["filename"] == clean_name:
            found = True
        else:
            remaining.append({
                "text": text,
                "filename": metadata["filename"],
                "page": metadata["page"],
            })

    if not found:
        raise ValueError(f"Document '{clean_name}' not found.")

    chroma_client.delete_collection(COLLECTION_NAME)
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if remaining:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(
            [record["text"] for record in remaining]
        )
        collection.add(
            ids=[f"chunk-{i}" for i in range(len(remaining))],
            documents=[record["text"] for record in remaining],
            metadatas=[
                {
                    "filename": record["filename"],
                    "page": int(record["page"]),
                }
                for record in remaining
            ],
            embeddings=matrix.toarray().astype(float).tolist(),
        )
        joblib.dump(vectorizer, VECTORIZER_PATH)
    else:
        if VECTORIZER_PATH.exists():
            VECTORIZER_PATH.unlink(missing_ok=True)

    return {
        "filename": clean_name,
        "status": "deleted",
    }




def ask(question: str) -> dict:
    """Answer questions using indexed document evidence and Gemini."""
    question = question.strip()

    if not question:
        return {
            "answer": "Please enter a question.",
            "sources": [],
        }

    if not VECTORIZER_PATH.exists():
        return {
            "answer": "No documents have been indexed yet.",
            "sources": [],
        }

    collection = _get_collection()
    if collection.count() == 0:
        return {
            "answer": "No documents have been indexed yet.",
            "sources": [],
        }

    vectorizer = joblib.load(VECTORIZER_PATH)
    query_vector = vectorizer.transform([question])

    if query_vector.nnz == 0:
        return {
            "answer": "I couldn't find a grounded answer in the indexed documents.",
            "sources": [],
        }

    results = collection.query(
        query_embeddings=query_vector.toarray().astype(float).tolist(),
        n_results=min(TOP_K, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    evidence = []
    sources = []
    retrieved = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - distance
        print(
            f"DEBUG | Source: {metadata['filename']} | "
            f"Similarity: {similarity:.3f}"
        )

        if similarity >= MIN_SIMILARITY:
            retrieved.append((document, metadata, similarity))

    if retrieved:
        best_similarity = max(item[2] for item in retrieved)

        # Keep results close to the best match.
        selected = [
            item for item in retrieved
            if item[2] >= best_similarity - 0.08
        ]

        for document, metadata, similarity in selected:
            source = f"{metadata['filename']}, p.{metadata['page']}"
            evidence.append(f"Source: {source}\nContent: {document}")

            if source not in sources:
                sources.append(source)

    if not evidence:
        return {
            "answer": "I couldn't find a grounded answer in the indexed documents.",
            "sources": [],
        }

        print(
    f"DEBUG | Source: {metadata['filename']} | "
    f"Similarity: {similarity:.3f}"
)

        source = f"{metadata['filename']}, p.{metadata['page']}"
        evidence.append(f"Source: {source}\nContent: {document}")

        if source not in sources:
            sources.append(source)

    if not evidence:
        return {
            "answer": "I couldn't find a grounded answer in the indexed documents.",
            "sources": [],
        }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to backend/.env."
        )

    from google import genai

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL")

    if not model:
        raise RuntimeError(
            "GEMINI_MODEL is missing. Set it to the model ID "
            "that worked in your Gemini connection test."
        )

    prompt = (
        "You are FinPilot AI, a financial document assistant.\n"
        "Answer using only the supplied document evidence.\n"
        "If the evidence does not answer the question, say so.\n"
        "Never invent financial figures. Clearly distinguish "
        "document facts from calculations.\n\n"
        f"Question: {question}\n\n"
        "Document evidence:\n"
        + "\n\n".join(evidence)
    )

    response = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            break
        except genai_errors.APIError as exc:
            status_code = getattr(exc, "code", None)

            if status_code not in (429, 500, 502, 503, 504):
                raise

            if attempt == 2:
                raise

            wait_seconds = 2 ** (attempt + 1)
            print(
                f"Gemini temporarily unavailable "
                f"(HTTP {status_code}). Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)

    answer = (response.text or "").strip()


    answer = (response.text or "").strip()

    if not answer:
        answer = "Gemini did not return an answer. Please try again."

    return {
        "answer": answer,
        "sources": sources,
    }
