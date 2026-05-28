import base64
import os

def embed():
    try:
        # 1. Lê a imagem
        if not os.path.exists('logo.png'):
            print("Erro: logo.png não encontrado!")
            return
            
        with open('logo.png', 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # 2. Lê o HTML
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        # 3. Substitui
        new_html = html.replace('src="logo.png"', f'src="data:image/png;base64,{img_data}"')
        
        # 4. Salva
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(new_html)
            
        print("Sucesso! Logo embutida no HTML.")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    embed()
