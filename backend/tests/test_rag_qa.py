
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from modules.documents import index_document, ask

# Index the sample invoice first
pdf_path = Path(__file__).parent / "sample_invoice.pdf"
index_result = index_document(
    pdf_path.name,
    pdf_path.read_bytes()
)
print("Indexing:", index_result)

# Ask questions whose answers are in the invoice
questions = [
    "What is the total invoice amount?",
    "Who is the supplier?",
    "What is the payment due date?",
]

for question in questions:
    print(f"\nQuestion: {question}")
    try:
        result = ask(question)
        print("Answer:", result["answer"])
        print("Sources:", result["sources"])
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
