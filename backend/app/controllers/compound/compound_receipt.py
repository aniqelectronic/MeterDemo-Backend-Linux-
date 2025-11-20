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
    # safe inline fallbacks
    compound_name = compound.name or "-"
    compound_no = compound.compoundnum or "-"
    compound_plate = compound.plate or "-"
    compound_date = compound.date.strftime("%Y-%m-%d")
    compound_time = compound.time.strftime("%H:%M")
    compound_offense = compound.offense or "-"
    compound_amount = f"{float(compound.amount):.2f}"

    pdf = FPDF()
    pdf.add_page()

    # ================= LOGO =================
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=70, y=10, w=70)
    logo_bottom = 10 + 50  # y + height

    # ================= TITLE =================
    pdf.set_xy(10, logo_bottom + 5)
    pdf.set_font("Arial", "B", 20)
    pdf.cell(190, 12, "COMPOUND E-RECEIPT", align="C")

    # Divider line
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, logo_bottom + 22, 190, logo_bottom + 22)

    # ================= DETAILS BOX =================
    box_x = 15
    box_y = logo_bottom + 30
    box_w = 180
    box_h = 115
    pad = 8
    inner_w = box_w - (pad * 2)

    # Box background
    pdf.set_fill_color(245, 247, 255)
    pdf.rect(box_x, box_y, box_w, box_h, style="F")

    # ----- Write inside box -----
    y = box_y + pad

    pdf.set_xy(box_x + pad, y)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(inner_w, 8, "Receipt Details", ln=True)

    pdf.set_font("Arial", "", 12)
    y += 12

    # Now place each line manually inside the box
    lines = [
        f"Name        : {compound_name}",
        f"Compound No : {compound_no}",
        f"Plate No    : {compound_plate}",
        f"Date        : {compound_date}",
        f"Time        : {compound_time}",
    ]

    for line in lines:
        pdf.set_xy(box_x + pad, y)
        pdf.cell(inner_w, 7, line, ln=True)
        y += 8

    # ---- Offense (multi-line inside box safely) ----
    pdf.set_xy(box_x + pad, y)
    pdf.multi_cell(inner_w, 7, f"Offense     : {compound_offense}")
    y = pdf.get_y()

    # ================= AMOUNT BOX =================
    amount_y = box_y + box_h + 10
    amount_h = 16

    pdf.set_fill_color(230, 240, 255)
    pdf.rect(box_x, amount_y, box_w, amount_h, style="F")

    pdf.set_xy(box_x, amount_y + 3)
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 80, 180)
    pdf.cell(box_w, 10, f"Amount: RM {compound_amount}", align="C")

    # ================= THANK YOU =================
    pdf.set_font("Arial", "I", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, amount_y + amount_h + 10)
    pdf.cell(190, 10, "Thank you for your payment!", align="C")

    # ================= FOOTER (always page 1 bottom) =================
    pdf.set_xy(10, 280)  # absolute position — no page 2 ever
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(190, 10, "2025 City Car Park System . All Rights Reserved", align="C")

    # Return bytes
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
