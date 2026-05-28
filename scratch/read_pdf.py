import pdfplumber
import os

pdf_path = r"c:\IA_dublagem\Estrutura de Dados - Unifatecie.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found!")
    exit(1)

print("Searching PDF...")
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            if "livro" in text.lower() or "doar" in text.lower() or "remover" in text.lower():
                print(f"--- Page {i + 1} ---")
                lines = text.split("\n")
                for line in lines:
                    if any(word in line.lower() for word in ["livro", "doar", "remover"]):
                        print(f"  {line}")
