
import sys
from pathlib import Path

# Add the backend directory to Python's import path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from modules.documents import index_document, ask


# For the first test, use an existing text-based PDF if available.
sample_path = Path(__file__).parent / "sample_invoice.pdf"

if not sample_path.exists():
    raise FileNotFoundError(
        "Please place a text-based sample invoice PDF at "
        "backend/tests/sample_invoice.pdf"
    )

content = sample_path.read_bytes()

print("Starting document indexing...", flush=True)

result = index_document("sample_invoice.pdf", content)

print("Document indexing finished.", flush=True)

print("Indexing result:", result)

assert result["filename"] == "sample_invoice.pdf"
assert result["status"] == "indexed"
assert result["chunks"] > 0

print("PASS: Document was indexed and chunks were stored.")