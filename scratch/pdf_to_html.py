import pdfplumber
import os
import html

pdf_path = r"c:\IA_dublagem\Estrutura de Dados - Unifatecie.pdf"
html_path = r"c:\IA_dublagem\Estrutura_de_Dados_Unifatecie.html"

if not os.path.exists(pdf_path):
    print("Erro: O arquivo 'Estrutura de Dados - Unifatecie.pdf' nao foi encontrado no caminho especificado.")
    exit(1)

print("Iniciando conversao do PDF para HTML...")
try:
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total de paginas detectadas: {total_pages}")
        
        with open(html_path, "w", encoding="utf-8") as f:
            # Cabecalho do documento HTML
            f.write("<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n")
            f.write("    <meta charset=\"UTF-8\">\n")
            f.write("    <title>Estrutura de Dados - UniFatecie (Texto Completo)</title>\n")
            f.write("    <style>\n")
            f.write("        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 20px; background-color: #0f172a; color: #e2e8f0; }\n")
            f.write("        .page { background-color: #1e293b; padding: 40px; margin-bottom: 25px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); border: 1px solid #334155; }\n")
            f.write("        h2 { border-bottom: 2px solid #3b82f6; padding-bottom: 8px; color: #3b82f6; margin-top: 0; font-size: 1.25rem; }\n")
            f.write("        .text-content { font-size: 1rem; white-space: pre-wrap; font-family: inherit; color: #cbd5e1; }\n")
            f.write("    </style>\n</head>\n<body>\n")
            f.write("    <h1 style=\"text-align: center; color: #3b82f6; margin-bottom: 40px;\">Estrutura de Dados - UniFatecie (Livro Didático)</h1>\n")
            
            # Processa e escreve pagina por pagina
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                text = page.extract_text()
                
                f.write(f'    <div class="page" id="page-{page_num}">\n')
                f.write(f'        <h2>Página {page_num}</h2>\n')
                f.write(f'        <div class="text-content">')
                
                if text:
                    # Escapa tags HTML para evitar interpretacao errada de codigos-fonte que possam estar no texto
                    escaped_text = html.escape(text)
                    f.write(escaped_text)
                else:
                    f.write("<em>[Página em branco ou contendo apenas imagens]</em>")
                
                f.write('</div>\n')
                f.write('    </div>\n\n')
                
                # Feedback de progresso no terminal
                if page_num % 10 == 0 or page_num == total_pages:
                    print(f"Progresso: {page_num}/{total_pages} paginas processadas...")
            
            # Fecha tags do documento
            f.write("</body>\n</html>\n")
            
    print(f"\nConversao concluida com sucesso! O arquivo foi salvo em:\n{html_path}")

except Exception as e:
    print(f"\nOcorreu um erro durante o processamento: {str(e)}")
