#!/usr/bin/env python3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

import os


def generate_sample_pdf(path: str):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 1.2 * inch, "Sample Document for Kindle Scribe Optimization")

    # Body text
    c.setFont("Times-Roman", 12)
    text = c.beginText(1 * inch, height - 2 * inch)
    lines = [
        "This is a test page containing text and a simple vector illustration.",
        "The optimizer will convert this to grayscale, crop margins, and fit it to Scribe.",
        "No words or illustrations will be altered—only format and sizing.",
        "",
        "Below is a rectangle with a circle inside (vector graphics):",
    ]
    for line in lines:
        text.textLine(line)
    c.drawText(text)

    # Simple vector illustration
    rect_x = 1.2 * inch
    rect_y = height - 5 * inch
    rect_w = 4 * inch
    rect_h = 2 * inch
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(2)
    c.rect(rect_x, rect_y, rect_w, rect_h, stroke=1, fill=0)

    c.setFillGray(0.8)
    c.circle(rect_x + rect_w / 2, rect_y + rect_h / 2, 0.6 * inch, stroke=1, fill=1)

    # Add some excess margins to test crop
    c.showPage()
    c.setFont("Times-Roman", 12)
    c.drawString(2 * inch, height - 2 * inch, "Page 2 — spaced content to test auto-crop and centering")

    c.save()


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "sample.pdf")
    generate_sample_pdf(out)
    print(f"Wrote {out}")
