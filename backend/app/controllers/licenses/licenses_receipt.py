from fpdf import FPDF
import fpdf
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
# MULTI COMPOUND RECEIPT PDF (REPORTLAB)
# =====================================================
def generate_multi_license_pdf(Licenses, total_amount):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    top_y = height - 80

    # ===== HEADER LOGO =====
    if LOGO_RL:
        img_w, img_h = LOGO_RL.getSize()
        w = 120
        h = (img_h / img_w) * w
        x = (width - w) / 2
        y = top_y - h
        pdf.drawImage(LOGO_RL, x, y, width=w, height=h, mask="auto")
        top_y = y - 40

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(width / 2, top_y, "MULTIPLE LICENSE RECEIPT")

    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, top_y - 20, "Official Transaction Record")

    y = top_y - 60

    # ===== TABLE HEADER =====
    pdf.setFillColor(colors.HexColor("#E9F0FF"))
    pdf.rect(40, y, 520, 28, fill=True, stroke=False)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 12)

    col_x = {
        "number": 50,
        "type": 200,
        "expiry": 360,
        "amount": 540
    }

    pdf.drawString(col_x["number"], y + 9, "License Number")
    pdf.drawString(col_x["type"], y + 9, "Type")
    pdf.drawString(col_x["expiry"], y + 9, "Expired Date")
    pdf.drawRightString(col_x["amount"], y + 9, "Amount (RM)")

    y -= 35
    pdf.setFont("Helvetica", 11)

    # ===== TABLE ROWS =====
    for idx, c in enumerate(Licenses):
        fill = colors.HexColor("#FAFAFA") if idx % 2 == 0 else colors.white
        pdf.setFillColor(fill)
        pdf.rect(40, y, 520, 22, fill=True, stroke=False)

        pdf.setFillColor(colors.black)

        pdf.drawString(col_x["number"], y + 6, str(c["licensenumber"]))
        pdf.drawString(col_x["type"], y + 6, str(c["licensetype"]))
        pdf.drawString(col_x["expiry"], y + 6, str(c["expired_date"]))

        pdf.drawRightString(col_x["amount"], y + 6, f"{float(c['amount']):.2f}")

        y -= 25

        # Page break
        if y <= 100:
            pdf.showPage()
            y = height - 120

    # ===== TOTAL =====
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.HexColor("#D6E9FF"))
    pdf.rect(40, y - 40, 520, 30, fill=True, stroke=False)

    pdf.setFillColor(colors.black)
    pdf.drawString(50, y - 20, "TOTAL AMOUNT:")
    pdf.drawRightString(540, y - 20, f"RM {total_amount:.2f}")

    # ===== FOOTER =====
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, 30, "2025 City Car Park System . All Rights Reserved")

    pdf.save()
    buffer.seek(0)
    return buffer
