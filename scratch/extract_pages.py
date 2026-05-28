import os

html_path = r"c:\IA_dublagem\Estrutura_de_Dados_Unifatecie.html"
output_path = r"c:\IA_dublagem\scratch\text_pages_65_71.txt"

if not os.path.exists(html_path):
    print("Erro: HTML nao encontrado")
    exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

import re
pages = re.split(r'<div class="page" id="page-\d+">', content)

with open(output_path, "w", encoding="utf-8") as out:
    for page_num in range(65, 72):
        if page_num < len(pages):
            out.write(f"=== PAGINA {page_num} ===\n")
            clean_text = re.sub('<[^<]+?>', '', pages[page_num]).strip()
            out.write(clean_text)
            out.write("\n\n" + "="*40 + "\n\n")

print("Paginas salvas com sucesso!")
