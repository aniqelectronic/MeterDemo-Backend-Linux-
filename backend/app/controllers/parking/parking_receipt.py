# app/utils/receipt.py
from fpdf import FPDF
import os
from io import BytesIO

class ReceiptPDF(FPDF):
    def __init__(self, logo_bytes=None):
        super().__init__()
        self.logo_bytes = logo_bytes

    def header(self):
        if self.logo_bytes:
            logo_width = 28
            # ✅ Use image from memory (no temp file)
            self.image(BytesIO(self.logo_bytes), x=(210 - logo_width) / 2, y=10, w=logo_width)
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


def generate_parking_receipt(ticket_id, plate, hours, time_in, time_out, amount, transaction_type, logo_bytes):
    pdf = ReceiptPDF(logo_bytes=logo_bytes)
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
        "Transaction Type": transaction_type,
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

    return pdf.output(dest="S").encode("latin1")
