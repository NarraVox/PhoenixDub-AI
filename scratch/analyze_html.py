import re
import os
import sys

html_path = r"c:\IA_dublagem\Estrutura_de_Dados_Unifatecie.html"
report_path = r"c:\IA_dublagem\scratch\analysis_report.txt"

if not os.path.exists(html_path):
    print("Erro: Arquivo HTML nao encontrado!")
    exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Buscando capitulos e secoes
unidades = re.findall(r"(UNIDADE\s+\d+|CAPITULO\s+\d+[^<]*)", content, re.IGNORECASE)

with open(report_path, "w", encoding="utf-8") as out:
    out.write("=== ESTRUTURA DETECTADA NO LIVRO ===\n")
    for u in sorted(list(set(unidades))):
        out.write(f"- {u}\n")
    
    out.write("\n=== DETALHAMENTO DE MENCOES RELEVANTES ===\n")
    
    pages = re.split(r'<div class="page" id="page-\d+">', content)
    
    for idx, page in enumerate(pages):
        page_num = idx
        if not page:
            continue
        
        page_text_lower = page.lower()
        keywords = ["livro", "doar", "remover", "estudo 1", "mapa", "excluir", "vetor", "lista", "fila", "pilha"]
        found_keywords = [kw for kw in keywords if kw in page_text_lower]
        
        if found_keywords:
            out.write(f"\n--- PAGINA {page_num} (Palavras-chave: {found_keywords}) ---\n")
            lines = page.split("<br>")
            printed_lines = 0
            for line in lines:
                clean_line = re.sub('<[^<]+?>', '', line).strip()
                # Remove multiplos espacos em branco
                clean_line = " ".join(clean_line.split())
                if any(kw in clean_line.lower() for kw in found_keywords) and len(clean_line) > 10:
                    out.write(f"  > {clean_line}\n")
                    printed_lines += 1
                    if printed_lines >= 8:
                        break
            out.write("-" * 50 + "\n")

print("Analise concluida e salva em c:\\IA_dublagem\\scratch\\analysis_report.txt")
