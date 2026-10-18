
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from pathlib import Path

# Save the second invoice in the tests folder.
output_path = Path(__file__).parent / "sample_invoice_2.pdf"

pdf = canvas.Canvas(str(output_path), pagesize=letter)
pdf.setTitle("Sample Office Supplies Invoice")

pdf.setFont("Helvetica-Bold", 18)
pdf.drawString(60, 740, "OFFICE SUPPLIES INVOICE")

pdf.setFont("Helvetica", 12)

invoice_details = [
    "Invoice Number: INV-2055",
    "Supplier: BlueSky Office Supplies",
    "Invoice Date: 18 October 2026",
    "Payment Due Date: 17 November 2026",
    "Product: Office notebooks",
    "Quantity: 200 units",
    "Unit Price: INR 80",
    "Subtotal: INR 16,000",
    "Tax: INR 2,880",
    "Total Amount: INR 18,880",
    "Payment Terms: Net 30 days",
]

y = 690
for line in invoice_details:
    pdf.drawString(60, y, line)
    y -= 30

pdf.setFont("Helvetica-Oblique", 10)
pdf.drawString(60, 300, "Fictional document created for FinPilot AI testing.")

pdf.save()

print(f"Second invoice created: {output_path}")
