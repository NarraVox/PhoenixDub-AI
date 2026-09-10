"""Consulta de releases oficiais, independente dos motores de IA."""
import os
import sys
import json
import threading
from pathlib import Path
import requests
from flask import Blueprint, jsonify, request
from nexus.version import APP_VERSION
from nexus.update_manager import UpdateManager
from nexus.update_worker import version_tuple, development_copy

REPOSITORY = "NarraVox/PhoenixDub-AI"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
updates_blueprint = Blueprint("updates", __name__)
manager = UpdateManager(Path(sys.executable).parent if getattr(sys, 'frozen', False)
                        else Path(__file__).resolve().parents[1])


def check_release():
    response = requests.get(API_URL, timeout=(4, 10), headers={
        "Accept": "application/vnd.github+json", "User-Agent": "PhoenixDub-Updater",
    })
    response.raise_for_status()
    release = response.json()
    if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
        raise ValueError("Nenhuma release pública estável disponível.")
    tag = release.get("tag_name", "")
    latest, current = version_tuple(tag), version_tuple(APP_VERSION)
    status = "available" if latest > current else "current" if latest == current else "ahead"
    release_url = f"{RELEASES_URL}/tag/{tag}"
    installer_url = None
    package = None
    for asset in release.get("assets", []):
        expected = f"https://github.com/{REPOSITORY}/releases/download/{tag}/Setup_Nexus.exe"
        if (asset.get("name") == "Setup_Nexus.exe" and asset.get("state") == "uploaded"
                and asset.get("browser_download_url") == expected):
            installer_url = expected
        package_url = f"https://github.com/{REPOSITORY}/releases/download/{tag}/PhoenixDub_Update.zip"
        if (asset.get('name') == 'PhoenixDub_Update.zip' and asset.get('state') == 'uploaded'
                and asset.get('browser_download_url') == package_url):
            package = {'url': package_url, 'size': int(asset.get('size') or 0), 'digest': asset.get('digest')}
    return {"success": True, "status": status, "current_version": APP_VERSION,
            "latest_version": tag.lstrip("v"), "has_update": status == "available",
            "release_url": release_url, "download_url": installer_url,
            "notes": str(release.get("body") or "Notas não disponíveis.")[:20000],
            "package": package, "development_copy": development_copy(manager.root),
            "automatic_supported": status == 'available' and package is not None and not development_copy(manager.root)}


@updates_blueprint.get("/api/check-update")
def check_update():
    try:
        return jsonify(check_release())
    except (requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
        return jsonify(success=False, status="error", current_version=APP_VERSION,
                       message="Não foi possível consultar as atualizações. Verifique a internet e tente novamente.",
                       release_url=RELEASES_URL), 503


@updates_blueprint.get("/api/app-version")
def app_version():
    return jsonify(current_version=APP_VERSION, development_copy=development_copy(manager.root))


def ensure_idle():
    import socket
    from nexus.nexus_app import active_engines
    from nexus.correction_routes import busy
    if busy() or any(e['process'] is not None and e['process'].poll() is None for e in active_engines.values()):
        raise ValueError('Aguarde as tarefas terminarem e volte ao Hub para encerrar os motores antes de atualizar.')
    for port in (5002, 5003, 5004, 5005):
        with socket.socket() as probe:
            probe.settimeout(.2)
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError('Ainda há um motor aberto. Encerre os motores antes de instalar a atualização.')


@updates_blueprint.before_request
def protect_update_actions():
    if request.method == 'POST':
        from urllib.parse import urlsplit
        origin = request.headers.get('Origin')
        if (request.headers.get('X-Nexus-Update') != '1'
                or (origin and (urlsplit(origin).hostname not in ('127.0.0.1', 'localhost')
                                or urlsplit(origin).port != 5000))):
            return jsonify(success=False, message='Origem de atualização inválida.'), 403


@updates_blueprint.post('/api/updates/download')
def download_update():
    try:
        ensure_idle()
        return jsonify(manager.start(check_release()))
    except (ValueError, requests.RequestException, OSError) as error:
        return jsonify(success=False, message=str(error)), 409


@updates_blueprint.get('/api/updates/status')
def update_status():
    return jsonify(manager.status())


@updates_blueprint.post('/api/updates/install')
def install_update():
    try:
        ensure_idle()
        manager.launch()
        timer = threading.Timer(1.5, lambda: os._exit(0))
        timer.daemon = True
        timer.start()
        return jsonify(success=True, message='Instalando e reiniciando o aplicativo...')
    except (ValueError, OSError) as error:
        return jsonify(success=False, message=str(error)), 409


@updates_blueprint.get('/api/updates/result')
def update_result():
    path = manager.root / '_updates/result.json'
    try:
        return jsonify(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, ValueError):
        return jsonify(None)
