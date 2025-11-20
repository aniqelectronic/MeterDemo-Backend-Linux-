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
# SINGLE COMPOUND RECEIPT PDF (FPDF 1.x SAFE)
# =====================================================
def generate_single_compound_pdf(compound):
    compound_name = compound.name or "-"
    compound_no = compound.compoundnum or "-"
    compound_plate = compound.plate or "-"
    compound_date = compound.date.strftime("%Y-%m-%d")
    compound_time = compound.time.strftime("%H:%M")
    compound_offense = compound.offense or "-"
    compound_amount = f"{float(compound.amount):.2f}"

    pdf = FPDF()
    pdf.add_page()

    # ========== LOGO ==========
    logo_height = 0
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=70, y=10, w=70)
        logo_height = 50  # actual height of logo (approx)

    # Move cursor BELOW logo
    start_y = 10 + logo_height + 20
    pdf.set_y(start_y)

    # ========== TITLE ==========
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "COMPOUND E-RECEIPT", ln=True, align="C")

    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y() + 3, 190, pdf.get_y() + 3)
    pdf.ln(10)

    # ========== DETAILS BOX ==========
    box_y = pdf.get_y()
    box_height = 110

    pdf.set_fill_color(245, 247, 255)
    pdf.set_draw_color(245, 247, 255)
    pdf.rect(15, box_y, 180, box_height, style="F")

    # Content inside box
    pdf.set_xy(20, box_y + 5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Receipt Details", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.ln(2)
    pdf.cell(0, 8, f"Name: {compound_name}", ln=True)
    pdf.cell(0, 8, f"Compound No: {compound_no}", ln=True)
    pdf.cell(0, 8, f"Plate No: {compound_plate}", ln=True)
    pdf.cell(0, 8, f"Date: {compound_date}", ln=True)
    pdf.cell(0, 8, f"Time: {compound_time}", ln=True)
    pdf.multi_cell(0, 8, f"Offense: {compound_offense}")

    # ========== AMOUNT BOX ==========
    amount_y = box_y + box_height + 12
    pdf.set_fill_color(230, 240, 255)
    pdf.set_draw_color(230, 240, 255)
    pdf.rect(15, amount_y, 180, 15, style="F")

    pdf.set_xy(15, amount_y)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 80, 180)
    pdf.cell(180, 15, f"Amount: RM {compound_amount}", align="C")

    # ========== FOOTER ==========
    pdf.set_y(-15)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Thank you for your payment!", ln=True, align="C")

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
    pdf.drawCentredString(width / 2, top_y, "MULTIPLE COMPOUND RECEIPT")

    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.grey)
    pdf.drawCentredString(width / 2, top_y - 20, "Official Transaction Record")

    y = top_y - 60

    # ===== TABLE HEADER =====
    pdf.setFillColor(colors.HexColor("#E9F0FF"))
    pdf.rect(40, y, 520, 28, fill=True, stroke=False)

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y + 9, "Compound Number")
    pdf.drawRightString(540, y + 9, "Amount (RM)")

    y -= 35
    pdf.setFont("Helvetica", 12)

    # ===== TABLE ROWS =====
    for idx, c in enumerate(compounds):
        fill = colors.HexColor("#FAFAFA") if idx % 2 == 0 else colors.white
        pdf.setFillColor(fill)
        pdf.rect(40, y, 520, 22, fill=True, stroke=False)

        pdf.setFillColor(colors.black)
        pdf.drawString(50, y + 6, c["compoundnum"])
        pdf.drawRightString(540, y + 6, f"{float(c['amount']):.2f}")

        y -= 25

        # page break
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
    pdf.drawCentredString(width / 2, 30, " 2025 City Car Park System . All Rights Reserved")

    pdf.save()
    buffer.seek(0)
    return buffer
