# Copyright (c) 2026 Paulo Henrik Carvalho de Araújo
# Licensed under the Apache License, Version 2.0

import os
import flask
from flask import Flask as OriginalFlask, request, jsonify
from pathlib import Path

# --- CONFIGURAÇÃO GLOBAL DE DIRETÓRIOS ---
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"

# Conjunto de caminhos permitidos dinamicamente (selecionados pelo usuário via file dialog)
allowed_stream_paths = set()

def register_allowed_path(path):
    """Registra um caminho de arquivo selecionado pelo usuário como seguro para streaming."""
    if path:
        abs_path = os.path.abspath(path)
        real_path = os.path.realpath(abs_path)
        allowed_stream_paths.add(real_path)
        # Também permite o formato em minúsculas para compatibilidade no Windows
        allowed_stream_paths.add(real_path.lower())

def is_safe_path(path_str):
    """Verifica se o caminho está dentro da pasta de uploads ou foi explicitamente permitido."""
    if not path_str:
        return False
    try:
        # Limpeza básica do caminho
        path_str = path_str.replace('file:///', '').replace('file://', '').replace('/', os.sep)
        if path_str.startswith(os.sep) and len(path_str) > 2 and path_str[2] == ':':
            path_str = path_str[1:]
        path_str = path_str.replace('"', '').replace("'", "").strip()

        resolved_path = os.path.realpath(os.path.abspath(path_str))
        resolved_uploads = os.path.realpath(os.path.abspath(UPLOAD_FOLDER))

        # 1. Verifica se está dentro da pasta uploads
        try:
            common = os.path.commonpath((resolved_uploads, resolved_path))
            if common == resolved_uploads:
                return True
        except ValueError:
            pass

        # 2. Verifica se foi explicitamente permitido na sessão atual
        if resolved_path in allowed_stream_paths or resolved_path.lower() in allowed_stream_paths:
            return True

        return False
    except Exception:
        return False

# --- MONKEYPATCH DO FLASK PARA SEGURANÇA GLOBAL (CORS & CSRF PROTECTION) ---
class SecuredFlask(OriginalFlask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        @self.before_request
        def check_origin_and_referer():
            # Apenas bloqueia requisições Cross-Origin (de navegadores externos)
            origin = request.headers.get('Origin')
            if origin:
                # Permite apenas conexões vindas do próprio localhost ou de file://
                if not (origin.startswith('http://127.0.0.1') or origin.startswith('http://localhost') or origin.startswith('file://')):
                    return jsonify({"error": "Forbidden: Cross-Origin Request Blocked"}), 403

            referer = request.headers.get('Referer')
            if referer:
                # Permite apenas conexões vindas do próprio localhost ou de file://
                if not (referer.startswith('http://127.0.0.1') or referer.startswith('http://localhost') or referer.startswith('file://')):
                    return jsonify({"error": "Forbidden: Cross-Origin Referer Blocked"}), 403

            # Filtro Global contra Path Traversal em rotas de streaming/mídia de qualquer motor
            if request.endpoint and any(k in request.endpoint.lower() for k in ['stream', 'media', 'file']):
                path_param = request.args.get('path') or request.args.get('video_path') or request.args.get('file_path') or request.args.get('file')
                if path_param:
                    if not is_safe_path(path_param):
                        return jsonify({"error": "Forbidden: Unsafe Path Traversal Blocked"}), 403

# Sobrescreve a classe Flask original para todas as importações subsequentes no projeto
flask.Flask = SecuredFlask
