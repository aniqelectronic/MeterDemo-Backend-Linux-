from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os

# === Preload logo once at startup for performance ===
LOGO = None
LOGO_PATH = "app/resources/images/PBT_Kuantan_logo.png"

try:
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            LOGO = ImageReader(BytesIO(f.read()))
        print("[INFO] Logo preloaded successfully.")
    else:
        print(f"[WARN] Logo not found at: {LOGO_PATH}")
except Exception as e:
    print(f"[WARN] Failed to load logo: {e}")


def generate_parking_receipt(
    ticket_id: str,
    plate: str,
    hours: float,
    time_in: datetime.datetime,
    time_out: datetime.datetime,
    amount: float,
    transaction_type: str,
):
    """
    Generate a parking receipt as PDF bytes using ReportLab (fast + memory-safe)
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4  # 595 x 842 points (A4 portrait)

    # === HEADER ===
    if LOGO:
        try:
            img_width, img_height = LOGO.getSize()
            display_width = 120
            aspect = img_height / img_width
            display_height = display_width * aspect

            # Center the logo horizontally
            x = (width - display_width) / 2
            y = height - (display_height + 60)

            c.drawImage(LOGO, x, y, width=display_width, height=display_height, mask='auto')
        except Exception as e:
            print(f"[WARN] Failed to draw logo: {e}")

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawCentredString(width / 2, height - 150, "PARKING E-RECEIPT")

    # Date
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, height - 170, datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"))

    # === DETAILS SECTION ===
    y = height - 210
    line_height = 22
    text_color = colors.HexColor("#000000")

    details = [
        ("Ticket ID", ticket_id),
        ("Plate Number", plate),
        ("Parking Duration", f"{hours:.2f} hour(s)"),
        ("Time In", time_in.strftime("%d/%m/%Y %I:%M %p")),
        ("Time Out", time_out.strftime("%d/%m/%Y %I:%M %p")),
        ("Transaction Type", transaction_type.capitalize()),
        ("Amount Paid (RM)", f"{amount:.2f}"),
    ]

    for label, value in details:
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(text_color)
        c.drawString(80, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(230, y, str(value))
        y -= line_height

    # === FOOTER ===
    c.setStrokeColor(colors.grey)
    c.line(60, 100, width - 60, 100)
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, 80, "Thank you for parking with us.")
    c.drawCentredString(width / 2, 65, "Have a safe journey!")

    # === FINALIZE PDF ===
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
