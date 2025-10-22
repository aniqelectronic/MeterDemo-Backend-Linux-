# app/utils/receipt.py
from fpdf import FPDF
import barcode
from barcode.writer import ImageWriter
import os
import tempfile


class ReceiptPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path

    def header(self):
        if self.logo_path and os.path.exists(self.logo_path):
            logo_width = 28
            self.image(self.logo_path, x=(210 - logo_width) / 2, y=10, w=logo_width)
        self.ln(50)

        self.set_font("Arial", 'B', 20)
        self.set_text_color(30, 30, 30)
        self.cell(0, 10, "PARKING E-RECEIPT", ln=True, align="C")
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.6)
        self.line(30, self.get_y(), 180, self.get_y())
        self.ln(10)

    def footer(self):
        self.set_y(-22)
        self.set_font("Arial", 'I', 11)
        self.set_text_color(90, 90, 90)
        self.cell(0, 10, "Thank you & Drive Safely!", 0, 0, 'C')


def generate_parking_receipt(ticket_id, plate, hours, time_in, time_out, amount, logo_path):
    """
    Generates a professional parking receipt PDF.
    Returns PDF bytes ready to upload or stream.
    """
    # --- Temporary barcode file
    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    barcode_img_path = tmp_file.name
    tmp_file.close()

    # --- Barcode generation
    code128 = barcode.get('code128', ticket_id, writer=ImageWriter())
    barcode_options = {"module_height": 7.0, "font_size": 8}
    code128.save(barcode_img_path.replace(".png", ""), options=barcode_options)
    barcode_img_path = barcode_img_path.replace(".png", ".png")

    # --- Create PDF
    pdf = ReceiptPDF(logo_path=logo_path)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_text_color(40, 40, 40)
    pdf.set_font("Arial", '', 12)

    info = {
        "Ticket ID": ticket_id,
        "Plate": plate,
        "Time Purchased (Hours)": hours,
        "Time In": time_in,
        "Time Out": time_out,
        "Amount": f"RM {amount:.2f}",
    }

    for label, value in info.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(60, 10, f"{label}:", border=0)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, str(value), border=0, ln=True)

    pdf.ln(15)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.4)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(15)

    barcode_width = 40
    barcode_x = (210 - barcode_width) / 2
    pdf.image(barcode_img_path, x=barcode_x, w=barcode_width)
    pdf.ln(8)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    os.remove(barcode_img_path)

    return pdf_bytes
