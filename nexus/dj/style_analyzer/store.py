"""Content-addressed artifacts. Never overwrite source or legacy projects."""
import hashlib
import json
from pathlib import Path

# Export constants for compatibility with openunmix.py and style_routes.py
TARGETS = ("drums", "bass", "vocals", "other")

from nexus.json_io import safe_json_read, safe_json_write
from . import VERSION


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    # Core helper logs failures instead of raising; verify persistence explicitly.
    safe_json_write(data, path, ensure_ascii=False)
    if safe_json_read(path) != data:
        raise OSError(f"Falha ao confirmar gravação: {path}")


def contained(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Caminho fora do projeto")
    return path


def manifest_versioned(project, paths):
    """Manifest including algorithm version for structural analysis."""
    project_path = Path(project)
    return {str(Path(p).relative_to(project_path)).replace("\\", "/"):
            {"sha256": digest(p), "size": Path(p).stat().st_size} for p in paths if Path(p).is_file()}


def valid_manifest_versioned(project, records):
    """Validate manifest with algorithm version check."""
    if not records:
        return False
    
    project_path = Path(project)
    
    # Check if style.json contains old algorithm version
    style = safe_json_read(project_path / "style.json") or {}
    current_version = VERSION
    stored_version = style.get("algorithm_version", None)
    
    # If versions don't match, analysis is considered invalid for re-use
    if stored_version != current_version:
        return False
    
    try:
        return all((p := contained(project_path, name)).is_file()
                   and p.stat().st_size == record["size"]
                   and digest(p) == record["sha256"] for name, record in records.items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def cache_key(source_hash, options, algorithm_version=None):
    """Generate cache key including algorithm version."""
    if algorithm_version is None:
        algorithm_version = VERSION
    
    import json
    combined = f"{algorithm_version}:{source_hash}:{json.dumps(options, sort_keys=True)}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:24]


def legacy_stems(project_root, manifest):
    """Check for legacy stems (pre-versioning)."""
    if not manifest:
        return False
    files = manifest.get("files", {})
    targets = ("drums", "bass", "vocals", "other")
    all_present = True
    for target in targets:
        path = project_root / f"{target}.wav"
        if not path.is_file():
            all_present = False
            break
    return all_present


def legacy_analysis(project_root, manifest):
    """Check if structural analysis exists and is usable."""
    style_path = project_root / "style.json"
    if not style_path.is_file():
        return None
    
    # Check version compatibility
    from . import VERSION
    style = safe_json_read(style_path) or {}
    stored_version = style.get("algorithm_version", None)
    if stored_version != VERSION:
        return {"valid": False, "reason": f"Algoritmo desatualizado ({stored_version} vs {VERSION})"}
    
    # Validate structure exists
    sections = style.get("sections")
    patterns = style.get("drums", {}).get("patterns")
    if not (isinstance(sections, list) and isinstance(patterns, list)):
        return {"valid": False, "reason": "Estrutura incompleta"}
    
    # Validate manifest integrity for structural files
    valid_manifest_versioned(project_root, manifest.get("files", {}))
    
    return {"valid": True}
