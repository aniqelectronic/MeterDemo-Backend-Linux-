from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime

# ✅ Preload logo once at startup (fast, cached in memory)
try:
    with open("app/resources/images/PBT_Kuantan_logo.png", "rb") as f:
        LOGO = ImageReader(BytesIO(f.read()))
except Exception as e:
    LOGO = None
    print(f"[WARN] Logo not found or unreadable: {e}")

def generate_parking_receipt(
    ticket_id: str,
    plate_number: str,
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
    width, height = A4  # (595.27 x 841.89 points)

    # === HEADER ===
    if LOGO:
        c.drawImage(LOGO, (width - 120) / 2, height - 120, width=120, height=60, mask='auto')

    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawCentredString(width / 2, height - 150, "PARKING E-RECEIPT")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, height - 170, datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"))

    # === DETAILS SECTION ===
    y = height - 210
    line_height = 22
    text_color = colors.HexColor("#000000")

    details = [
        ("Ticket ID", ticket_id),
        ("Plate Number", plate_number),
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
