from fpdf import FPDF
import html
from app.utils.blob_upload import upload_to_blob
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# =====================================================
# Generate SINGLE COMPOUND RECEIPT PDF
# =====================================================
def generate_single_compound_pdf(compound):
    """
    Generate PDF and return uploaded Blob URL
    """

    # Escape to avoid invalid characters
    compound_name = html.escape(compound.name or "-")
    compound_no = html.escape(compound.compoundnum)
    compound_plate = html.escape(compound.plate or "-")      # FIXED
    compound_date = compound.date.strftime("%Y-%m-%d")
    compound_time = compound.time.strftime("%H:%M")
    compound_offense = html.escape(compound.offense or "-")
    compound_amount = f"{float(compound.amount):.2f}"

    # ========== BUILD PDF ==========
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Compound E-Receipt", ln=True, align="C")

    pdf.ln(5)
    pdf.set_font("Arial", "", 12)

    pdf.cell(0, 8, f"Name: {compound_name}", ln=True)
    pdf.cell(0, 8, f"Compound No: {compound_no}", ln=True)
    pdf.cell(0, 8, f"Plate: {compound_plate}", ln=True)
    pdf.cell(0, 8, f"Date: {compound_date}", ln=True)
    pdf.cell(0, 8, f"Time: {compound_time}", ln=True)
    pdf.cell(0, 8, f"Offense: {compound_offense}", ln=True)
    pdf.cell(0, 8, f"Amount: RM {compound_amount}", ln=True)

    pdf.ln(10)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    filename = f"compound_{compound_no}.pdf"

    # Upload to Azure Blob
    return upload_to_blob(
        filename,
        pdf_bytes,
        content_type="application/pdf"
    )
    
    
# =====================================================
# Generate MULTI COMPOUND RECEIPT PDF
# =====================================================
def generate_multi_compound_pdf(compounds, total_amount):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "Multiple Compound Receipt")
    y -= 40

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Compound Number")
    pdf.drawString(320, y, "Amount (RM)")
    y -= 25
    pdf.line(50, y, 550, y)
    y -= 20

    pdf.setFont("Helvetica", 12)

    for c in compounds:
        pdf.drawString(50, y, c.get("compoundnum"))
        pdf.drawString(320, y, f"RM {float(c.get('amount',0)):.2f}")
        y -= 20

        # New page
        if y < 100:
            pdf.showPage()
            y = 800
            pdf.setFont("Helvetica", 12)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y - 20, f"TOTAL: RM {total_amount:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer