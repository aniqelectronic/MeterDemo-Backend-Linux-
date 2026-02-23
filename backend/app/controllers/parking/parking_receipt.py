from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os

# === Preload logo once at startup for performance ===
LOGO = None
LOGO_PATH = "app/resources/images/City_Car_Park_logo.png"

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
    Generate a modern parking receipt (PDF bytes) using ReportLab.
    Clean, stable, and backend-safe.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- HEADER SECTION ---
    top_y = height - 100
    text_after_logo_y = top_y - 30

    # Logo
    if LOGO:
        try:
            img_width, img_height = LOGO.getSize()
            display_width = 120
            aspect = img_height / img_width
            display_height = display_width * aspect

            x = (width - display_width) / 2
            y = top_y - display_height

            c.drawImage(LOGO, x, y, width=display_width, height=display_height, mask="auto")
            text_after_logo_y = y - 25

        except Exception as e:
            print(f"[WARN] Failed to draw logo: {e}")

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(colors.HexColor("#222222"))
    c.drawCentredString(width / 2, text_after_logo_y, "PARKING E-RECEIPT")

    # Date
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.grey)
    c.drawCentredString(
        width / 2,
        text_after_logo_y - 18,
        datetime.datetime.now().strftime("%d %b %Y, %I:%M %p"),
    )

    # --- TABLE SECTION ---
    y = text_after_logo_y - 70
    table_left = 60
    table_right = width - 60
    row_height = 30
    corner_radius = 10

    details = [
        ("Ticket ID", ticket_id),
        ("Plate Number", plate),
        ("Parking Duration", f"{hours:.2f} hour(s)"),
        ("Time In", time_in.replace(second=0, microsecond=0).strftime("%d/%m/%Y %I:%M %p")),
        ("Time Out", time_out.replace(second=0, microsecond=0).strftime("%d/%m/%Y %I:%M %p")),
        ("Transaction Type", transaction_type.capitalize()),
        ("Amount Paid (RM)", f"{amount:.2f}"),
    ]

    total_rows = len(details) + 1  # header row included
    table_height = total_rows * row_height

    # Shadow
    c.setFillColor(colors.HexColor("#DDDDDD"))
    c.roundRect(
        table_left + 3,
        y - table_height - 3,
        (table_right - table_left),
        table_height + 6,
        corner_radius,
        fill=True,
        stroke=False,
    )

    # Table background
    c.setFillColor(colors.white)
    c.roundRect(
        table_left,
        y - table_height,
        (table_right - table_left),
        table_height,
        corner_radius,
        fill=True,
        stroke=False,
    )

    # Table header row
    c.setFillColor(colors.HexColor("#F2F2F2"))
    c.rect(table_left, y - row_height, (table_right - table_left), row_height, fill=True, stroke=False)
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(colors.black)
    c.drawString(table_left + 12, y - row_height + 8, "Parking Details")

    y -= row_height

    # Table rows
    for index, (label, value) in enumerate(details):
        # Striping
        if index % 2 == 0:
            c.setFillColor(colors.HexColor("#FAFAFA"))
        else:
            c.setFillColor(colors.white)

        c.rect(table_left, y - row_height, (table_right - table_left), row_height, fill=True, stroke=False)

        # Label
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.HexColor("#222222"))
        c.drawString(table_left + 15, y - row_height + 9, label)

        # Value (right-aligned)
        c.setFont("Helvetica", 11)
        c.setFillColor(colors.HexColor("#444444"))
        c.drawRightString(table_right - 15, y - row_height + 9, str(value))

        y -= row_height

    # --- FOOTER ---
    c.setStrokeColor(colors.grey)
    c.line(60, 100, width - 60, 100)

    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, 80, "Thank you for parking with us.")
    c.drawCentredString(width / 2, 65, "Have a safe journey!")

    # Finalize PDF
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()
