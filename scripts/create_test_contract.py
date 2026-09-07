import json
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


BASE_DIR = Path(__file__).resolve().parent.parent

input_file = BASE_DIR / "data" / "cuad" / "contracts" / "CUADv1.json"
output_file = BASE_DIR / "data" / "cuad" / "test_contract.pdf"


with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)


contract = data["data"][0]

title = contract["title"]
text = contract["paragraphs"][0]["context"]


pdf = canvas.Canvas(
    str(output_file),
    pagesize=letter
)

width, height = letter

margin = 40
y = height - margin

pdf.setTitle(title)

pdf.setFont("Helvetica-Bold", 12)
pdf.drawString(
    margin,
    y,
    title[:100]
)

y -= 25

pdf.setFont("Helvetica", 9)

# Break the contract into printable lines.
for paragraph in text.splitlines():

    paragraph = paragraph.strip()

    if not paragraph:
        y -= 10
        continue

    # Wrap long lines.
    while len(paragraph) > 100:

        line = paragraph[:100]

        pdf.drawString(
            margin,
            y,
            line
        )

        paragraph = paragraph[100:]

        y -= 12

        if y < margin:

            pdf.showPage()

            pdf.setFont("Helvetica", 9)

            y = height - margin

    if paragraph:

        pdf.drawString(
            margin,
            y,
            paragraph
        )

        y -= 12

    if y < margin:

        pdf.showPage()

        pdf.setFont("Helvetica", 9)

        y = height - margin


pdf.save()

print(f"Created: {output_file}")
print(f"Title: {title}")
print(f"Characters: {len(text)}")