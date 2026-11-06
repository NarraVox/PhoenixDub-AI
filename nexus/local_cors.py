# -*- coding: utf-8 -*-
"""CORS restrito ao próprio computador.

As interfaces do PhoenixDub abrem em http://127.0.0.1:5000 e chamam os outros
serviços locais (5001, 5003...). Só essas origens locais podem chamar as APIs;
páginas de sites externos abertas no navegador ficam bloqueadas.
"""

LOCAL_ORIGINS = [r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$"]


def allow_local_origins(app):
    """Aplica CORS liberando apenas 127.0.0.1/localhost, em qualquer porta."""
    from flask_cors import CORS
    return CORS(app, origins=LOCAL_ORIGINS)
