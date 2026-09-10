"""Empacota código e interfaces; sem arquivos de trabalho ou modelos."""
from pathlib import Path
import zipfile
import importlib.util


def build_runtime(root):
    root = Path(root)
    spec = importlib.util.spec_from_file_location('update_worker_build', root/'nexus/update_worker.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = root/'dist/runtime.zip'
    output.parent.mkdir(exist_ok=True)
    paths = [root/'Nexus_AI_Pro.py', root/'requirements.txt', root/'vpk_manager.py']
    paths += [p for p in (root/'nexus').rglob('*') if p.is_file() and module.allowed_path(p.relative_to(root).as_posix())]
    paths += [root/'nexus/core/server_config.json']
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as package:
        for path in paths:
            package.write(path, path.relative_to(root).as_posix())
    return output
