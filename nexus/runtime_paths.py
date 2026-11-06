"""Resolve paths to locally installed runtime tools."""
from pathlib import Path


def resolve_vgmstream_path(project_root: Path) -> Path:
    """Prefer the development environment install, with legacy release fallback."""
    project_root = Path(project_root)
    environment_path = project_root / "env" / "tools_vgmstream" / "vgmstream-cli.exe"
    legacy_path = project_root / "tools" / "vgmstream-cli" / "vgmstream-cli.exe"
    if environment_path.is_file() or not legacy_path.is_file():
        return environment_path
    return legacy_path
