# app/utils/pdf_generator.py
from weasyprint import HTML

def generate_pdf_from_html(html_content: str, output_file: str):
    HTML(string=html_content).write_pdf(output_file)
    return output_file
