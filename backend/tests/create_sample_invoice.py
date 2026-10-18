
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

output_path = Path(__file__).parent / "sample_invoice.pdf"

pdf = canvas.Canvas(str(output_path), pagesize=letter)

pdf.setTitle("Sample Retail Supplier Invoice")

pdf.setFont("Helvetica-Bold", 18)
pdf.drawString(60, 740, "RETAIL SUPPLIER INVOICE")

pdf.setFont("Helvetica", 12)

invoice_details = [
    "Invoice Number: INV-1042",
    "Supplier: GreenLeaf Packaging Supplies",
    "Invoice Date: 17 October 2026",
    "Payment Due Date: 16 November 2026",
    "Product: Corrugated shipping boxes",
    "Quantity: 500 units",
    "Unit Price: INR 50",
    "Subtotal: INR 25,000",
    "Tax: INR 4,500",
    "Total Amount: INR 29,500",
    "Payment Terms: Net 30 days",
]

y = 690

for line in invoice_details:
    pdf.drawString(60, y, line)
    y -= 30

pdf.setFont("Helvetica-Oblique", 10)
pdf.drawString(60, 300, "Fictional document created for FinPilot AI testing.")

pdf.save()

print(f"Sample invoice created: {output_path}")
