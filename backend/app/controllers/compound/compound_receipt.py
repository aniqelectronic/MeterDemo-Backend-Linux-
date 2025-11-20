from fpdf import FPDF
import html
from app.utils.blob_upload import upload_to_blob
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import os

# =====================================================
# LOGO HANDLING
# =====================================================

LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"

# ReportLab ImageReader (used ONLY for multi PDF)
LOGO_RL = None
if os.path.exists(LOGO_PATH):
    try:
        with open(LOGO_PATH, "rb") as f:
            LOGO_RL = ImageReader(BytesIO(f.read()))
        print("[INFO] Logo loaded for ReportLab multi-PDF")
    except Exception as e:
        print(f"[WARN] Failed to load ReportLab logo: {e}")
else:
    print(f"[WARN] Logo path does not exist: {LOGO_PATH}")


# =====================================================
# SINGLE COMPOUND RECEIPT PDF (FPDF)
# =====================================================
def generate_single_compound_pdf(compound):
    """
    Generate PDF and upload to blob storage. Returns URL.
    """

    # Escape fields
    compound_name = html.escape(compound.name or "-")
    compound_no = html.escape(compound.compoundnum)
    compound_plate = html.escape(compound.plate or "-")
    compound_date = compound.date.strftime("%Y-%m-%d")
    compound_time = compound.time.strftime("%H:%M")
    compound_offense = html.escape(compound.offense or "-")
    compound_amount = f"{float(compound.amount):.2f}"

    # ==== Build PDF ====
    pdf = FPDF()
    pdf.add_page()

    # --- LOGO (FPDF requires FILE PATH, NOT ImageReader) ---
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=75, y=10, w=60)
        pdf.ln(40)

    # --- TITLE ---
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Compound E-Receipt", ln=True, align="C")
    pdf.ln(5)

    # --- DETAILS ---
    pdf.set_font("Arial", "", 13)
    pdf.cell(0, 9, f"Name: {compound_name}", ln=True)
    pdf.cell(0, 9, f"Compound No: {compound_no}", ln=True)
    pdf.cell(0, 9, f"Plate No: {compound_plate}", ln=True)
    pdf.cell(0, 9, f"Date: {compound_date}", ln=True)
    pdf.cell(0, 9, f"Time: {compound_time}", ln=True)
    pdf.multi_cell(0, 9, f"Offense: {compound_offense}")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 15)
    pdf.set_text_color(0, 102, 204)
    pdf.cell(0, 12, f"Amount: RM {compound_amount}", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)

    pdf.ln(6)
    pdf.set_font("Arial", "I", 12)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

    # Output as bytes
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    filename = f"compound_{compound_no}.pdf"

    return upload_to_blob(filename, pdf_bytes, "application/pdf")


# =====================================================
# MULTI COMPOUND RECEIPT PDF (REPORTLAB)
# =====================================================
def generate_multi_compound_pdf(compounds, total_amount):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    top_y = height - 100

    # --- LOGO ---
    if LOGO_RL:
        img_w, img_h = LOGO_RL.getSize()
        w = 110
        h = (img_h / img_w) * w
        x = (width - w) / 2
        y = top_y - h
        pdf.drawImage(LOGO_RL, x, y, width=w, height=h, mask="auto")
        top_y = y - 25

    # --- TITLE ---
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, top_y, "MULTIPLE COMPOUND RECEIPT")

    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, top_y - 18, "Generated Summary")

    y = top_y - 60

    # --- TABLE HEADER ---
    pdf.setFont("Helvetica-Bold", 14)
    pdf.setFillColor(colors.HexColor("#F2F2F2"))
    pdf.rect(50, y, 500, 30, fill=True, stroke=False)
    pdf.setFillColor(colors.black)
    pdf.drawString(60, y + 9, "Compound Number")
    pdf.drawString(350, y + 9, "Amount (RM)")

    y -= 40
    pdf.setFont("Helvetica", 12)

    # --- TABLE CONTENT ---
    for idx, c in enumerate(compounds):
        fill = colors.HexColor("#FAFAFA") if idx % 2 == 0 else colors.white
        pdf.setFillColor(fill)
        pdf.rect(50, y, 500, 25, fill=True, stroke=False)

        pdf.setFillColor(colors.black)
        pdf.drawString(60, y + 7, c.get("compoundnum"))
        pdf.drawRightString(520, y + 7, f"RM {float(c['amount']):.2f}")

        y -= 30

        if y <= 100:
            pdf.showPage()
            y = height - 150

    # --- TOTAL ---
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.black)
    pdf.drawString(50, y - 20, f"TOTAL: RM {total_amount:.2f}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    return buffer
