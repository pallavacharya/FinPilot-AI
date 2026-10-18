
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from modules.documents import index_document, ask

TEST_DIR = Path(__file__).parent

# Index both invoices.
for filename in ["sample_invoice.pdf", "sample_invoice_2.pdf"]:
    path = TEST_DIR / filename
    result = index_document(filename, path.read_bytes())
    print("Indexing:", result)

questions = [
    "What is the total amount of invoice INV-1042?",
    "Who supplied the office notebooks?",
    "What is the total amount of invoice INV-2055?",
    "What is the payment due date for BlueSky Office Supplies?",
]

for question in questions:
    print(f"\nQuestion: {question}")
    try:
        result = ask(question)
        print("Answer:", result["answer"])
        print("Sources:", result["sources"])
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
