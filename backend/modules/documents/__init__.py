"""RAG PIPELINE (DOCUMENT Q&A)  -  owner: Pallav Acharya (Lead)

Replace the bodies of index_document() and ask() with your chunking ->
embeddings -> ChromaDB -> Claude API pipeline. Keep the function names,
arguments and return keys EXACTLY as below.
Put your Claude API key in a .env file (never commit it).
"""

# --- sample answers (delete once the real pipeline is connected) ---
_SAMPLE = {
    "how much did we spend on suppliers last quarter?": {
        "answer": "Total supplier spend for Q2 was \u20b96,84,200, across 11 invoices. The largest single payment was \u20b91,20,000 to Nimbus Packaging on May 14.",
        "sources": ["invoice_may14.pdf, p.1", "invoice_summary_q2.pdf, p.2"],
    },
    "which invoice has the highest amount?": {
        "answer": "The highest invoice on file is INV-2091 for \u20b91,42,000, billed by Meridian Wholesale on June 3.",
        "sources": ["INV-2091.pdf, p.1"],
    },
    "any overdue payments?": {
        "answer": "Yes \u2014 2 invoices are overdue: INV-2077 (\u20b928,400, due 12 days ago) and INV-2088 (\u20b99,150, due 3 days ago).",
        "sources": ["INV-2077.pdf", "INV-2088.pdf"],
    },
}


def index_document(filename: str, content: bytes) -> dict:
    """Chunk, embed and store an uploaded document.

    Args:
        filename: original file name, e.g. "invoice_may14.pdf"
        content:  the raw file bytes
    Returns:
        {"filename": str, "status": "indexed", "chunks": int}
    """
    return {"filename": filename, "status": "indexed", "chunks": 0}


def ask(question: str) -> dict:
    """Answer a question using only the indexed documents.

    Returns:
        {
          "answer": str,
          "sources": [str, ...],          # e.g. ["invoice_may14.pdf, p.1"]  (empty list if none)
        }
    """
    hit = _SAMPLE.get(question.lower().strip())
    if hit:
        return hit
    return {
        "answer": "I couldn't find a grounded answer to that in the indexed documents.",
        "sources": [],
    }
