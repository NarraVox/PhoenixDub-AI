import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import pdfplumber
import easyocr
import traceback
from PIL import Image

# Importando as funções do núcleo
import nexus_core as core

app = Flask(__name__)
CORS(app)

# EasyOCR baixará o modelo automaticamente na primeira vez.

# Diretório para uploads temporários de docs
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads" / "docs"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Variável global para armazenar o contexto do último documento carregado
current_document_context = ""

@app.route('/api/docs/process', methods=['POST'])
def process_document():
    import json
    from flask import Response, stream_with_context
    
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"})
    
    files = request.files.getlist('files')
    if not files and 'file' in request.files:
        files = [request.files['file']]
        
    if not files or all(f.filename == '' for f in files):
        return jsonify({"success": False, "error": "Arquivos vazios"})
        
    # Salvar temporariamente para não perder o request context
    saved_files = []
    for f in files:
        if f.filename != '':
            path = UPLOAD_FOLDER / f.filename
            f.save(path)
            saved_files.append((f.filename, path))

    def generate():
        global current_document_context
        import time
        start_time = time.time()
        
        has_images = any(f[0].split('.')[-1].lower() in ['png', 'jpg', 'jpeg'] for f in saved_files)
        
        # O total de tarefas base é 2 (Início e Fim).
        total_steps = 2
        if has_images:
            total_steps += 2 # 1 para carregar OCR na VRAM, 1 para limpar VRAM no final
            
        for f, _ in saved_files:
            if f.endswith('.pdf'): total_steps += 2 # Abrindo e extraindo
            else: total_steps += 2 # Analisando e extraindo
            
        current_step = 1
        
        try:
            yield json.dumps({"progress": 5, "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Recebidos {len(saved_files)} arquivo(s). Preparando leitura..."}) + "\n"
            current_step += 1
            combined_extracted_text = ""
            
            reader = None
            if has_images:
                import torch
                import easyocr
                
                is_gpu = torch.cuda.is_available()
                device_name = "Placa de Vídeo (GPU)" if is_gpu else "Processador (CPU - MODO LENTO!)"
                
                yield json.dumps({"progress": 10, "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Iniciando motor EasyOCR no {device_name}..."}) + "\n"
                current_step += 1
                
                # Se não tem CUDA, avisa no log também
                if not is_gpu:
                    print("AVISO: PyTorch não detectou CUDA. O EasyOCR está rodando na CPU!")
                
                reader = easyocr.Reader(['pt', 'en'], gpu=is_gpu)
            
            for idx, (filename, file_path) in enumerate(saved_files):
                base_prog = 15 + (idx / len(saved_files)) * 75
                step_size = 75 / len(saved_files)
                
                yield json.dumps({"progress": int(base_prog), "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Analisando arquivo {idx+1}/{len(saved_files)}: {filename}"}) + "\n"
                current_step += 1
                
                file_ext = filename.split('.')[-1].lower()
                extracted_text = ""
                
                if file_ext == 'pdf':
                    yield json.dumps({"progress": int(base_prog + step_size*0.2), "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Extraindo textos do documento PDF..."}) + "\n"
                    current_step += 1
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text: extracted_text += text + "\n"
                
                elif file_ext in ['png', 'jpg', 'jpeg']:
                    import numpy as np
                    from PIL import Image, ImageOps
                    
                    img = Image.open(file_path)
                    # CORREÇÃO CRÍTICA: Aplica a rotação do celular (EXIF)
                    # Sem isso, fotos verticais são lidas de lado e geram lixo como "g ; 1 | 1 {"
                    img = ImageOps.exif_transpose(img)
                    img = img.convert('RGB')
                    
                    img_array = np.array(img)
                    
                    device_msg = "GPU PyTorch" if is_gpu else "CPU"
                    yield json.dumps({"progress": int(base_prog + step_size*0.5), "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Extraindo textos da imagem via {device_msg}..."}) + "\n"
                    current_step += 1
                    
                    # Otimizações pesadas para documentos com letras minúsculas e densos
                    results = reader.readtext(
                        img_array, 
                        detail=0,
                        paragraph=True, # Junta blocos de texto em parágrafos coerentes
                        canvas_size=max(img_array.shape[0], img_array.shape[1], 2560), # Impede a IA de encolher a imagem internamente
                        mag_ratio=1.2 # Leve zoom digital para ajudar a ler letrinhas
                    )
                    extracted_text = "\n\n".join(results)
                    
                else:
                    yield json.dumps({"success": False, "error": f"Formato .{file_ext} não suportado no arquivo {filename}."}) + "\n"
                    return
                
                if extracted_text.strip():
                    if len(saved_files) > 1:
                        combined_extracted_text += f"\n\n--- DOCUMENTO: {filename} ---\n\n"
                    combined_extracted_text += extracted_text + "\n"
                    
                if file_path.exists():
                    os.remove(file_path)
            
            if has_images:
                yield json.dumps({"progress": 95, "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": f"Limpando VRAM..."}) + "\n"
                current_step += 1
                del reader
                import gc
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except: pass
                
            if not combined_extracted_text.strip():
                yield json.dumps({"success": False, "error": "Nenhum texto foi encontrado nas imagens/arquivos."}) + "\n"
                return
                
            current_document_context = combined_extracted_text
            yield json.dumps({"progress": 100, "step": current_step, "total_steps": total_steps, "elapsed": round(time.time() - start_time, 2), "message": "Leitura concluída com sucesso!", "success": True, "text": combined_extracted_text}) + "\n"
            
        except Exception as e:
            err_msg = traceback.format_exc()
            print(f"============ ERRO CRÍTICO NO OCR ============\n{err_msg}\n=============================================")
            yield json.dumps({"success": False, "error": "Erro no motor OCR: " + str(e)}) + "\n"
            
    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')

@app.route('/api/docs/chat', methods=['POST'])
def chat_with_document():
    global current_document_context
    data = request.json
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        return jsonify({"success": False, "error": "Prompt vazio."})
        
    if not current_document_context:
        return jsonify({"success": False, "error": "Nenhum documento carregado para conversar."})

    try:
        engine = core.get_local_gemma_engine()
        
        # [v2026.RAG_AGENT] Fatiamento Inteligente de Contexto (Chunking)
        import textwrap
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Divide o documento gigante em pedaços (ex: 500 caracteres cada)
        chunks = textwrap.wrap(current_document_context, width=500, break_long_words=False, replace_whitespace=False)
        
        if len(chunks) > 3:
            # Agente Investigador: Procura na velocidade da luz (TF-IDF CPU) os pedaços relevantes
            vectorizer = TfidfVectorizer().fit(chunks + [user_prompt])
            vectors = vectorizer.transform(chunks + [user_prompt])
            
            chunk_vectors = vectors[:-1]
            prompt_vector = vectors[-1]
            
            # Calcula a similaridade entre a pergunta e cada pedaço
            similarities = cosine_similarity(prompt_vector, chunk_vectors)[0]
            
            # Pega o índice dos 4 pedaços mais parecidos/relevantes com a pergunta
            top_indices = similarities.argsort()[-4:][::-1]
            relevant_context = "\n...\n".join([chunks[i] for i in top_indices])
        else:
            # Se o documento for pequeno (ex: um recibo simples), passa tudo.
            relevant_context = current_document_context

        full_prompt = (
            f"Você é o assistente Nexus Docs.\n"
            f"Aqui estão as informações extraídas e mais relevantes do documento:\n\n"
            f"\"\"\"{relevant_context}\"\"\"\n\n"
            f"Responda à pergunta baseando-se apenas nos trechos acima:\nPergunta: {user_prompt}"
        )
        
        if hasattr(engine, 'create_chat_completion'):
             response = engine.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Você é o assistente Nexus Docs, analisador de documentos."},
                    {"role": "user", "content": full_prompt}
                ]
            )
             reply = response['choices'][0]['message']['content']
        else:
            reply = engine(full_prompt, max_new_tokens=500)[0]['generated_text']

        return jsonify({"success": True, "response": reply})

    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"============ ERRO CRÍTICO NO CHAT ============\n{err_msg}\n=============================================")
        return jsonify({"success": False, "error": f"Erro no Agente:\n{err_msg}"})

@app.route('/api/docs/generate_design', methods=['GET'])
def generate_design():
    try:
        engine = core.get_local_gemma_engine()
        prompt = (
            "Atue como um Web Designer e UI/UX expert de alto nível. "
            "Crie o código HTML e CSS completo de uma página MARAVILHOSA, de cair o queixo, "
            "para exibir a leitura de um documento escaneado.\n\n"
            "DIRETRIZES DE DESIGN OBRIGATÓRIAS:\n"
            "- Estilo Dark Mode Premium (Fundo profundo e elegante, com sombras suaves e detalhes em Neon/Cyberpunk).\n"
            "- Use 'Glassmorphism' (painéis com fundo semi-transparente, bordas finas e backdrop-filter: blur).\n"
            "- O TÍTULO da página deve ser gigante e lindíssimo, com efeitos de gradiente no texto (background-clip: text).\n"
            "- Importe fontes modernas do Google Fonts (ex: 'Outfit', 'Inter' ou 'Space Grotesk').\n"
            "- Adicione sombras brilhantes (glow) e botões que reagem magicamente ao passar o mouse (hover effects).\n\n"
            "REGRAS TÉCNICAS (CRÍTICAS):\n"
            "1. Retorne APENAS o código HTML puro. JAMAIS use marcações como ```html.\n"
            "2. O código deve ter <style> e <script> embutidos num único arquivo.\n"
            "3. Inclua um botão 'COPIAR TUDO' estilizado que copie o conteúdo da div principal ao clicar.\n"
            "4. A MAIS IMPORTANTE: Crie um cartão de vidro lindo para o conteúdo e, dentro dele, coloque EXATAMENTE esta tag vazia: <div id=\"nexus-content\"></div> (É nela que meu servidor Python injetará as 50 páginas de texto real)."
        )
        
        if hasattr(engine, 'create_chat_completion'):
             response = engine.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Você é um Diretor de Arte Front-End de Hollywood. Suas interfaces são obras de arte premiadas, riquíssimas em CSS moderno, animações sutis e estética deslumbrante."},
                    {"role": "user", "content": prompt}
                ]
            )
             reply = response['choices'][0]['message']['content']
        else:
            reply = engine(prompt, max_new_tokens=1500)[0]['generated_text']
            
        # Garante que não haja restos de markdown
        reply = reply.replace("```html", "").replace("```", "").strip()
        
        return jsonify({"success": True, "design": reply})
    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"============ ERRO NO GEMMA HTML ============\n{err_msg}\n=============================================")
        return jsonify({"success": False, "error": f"Erro ao gerar design no Gemma 4:\n{err_msg}"})

if __name__ == '__main__':
    print("=======================================")
    print("📄 NEXUS DOCS ENGINE - ATIVO")
    print("=======================================")
    # Rodando numa porta diferente para não conflitar com o vortex_dj ou o app principal
    app.run(port=5006)
