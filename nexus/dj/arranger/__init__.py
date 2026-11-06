"""Nexus Arranger MVP: deterministic symbolic arrangement plans."""

from .planning import build_arrangement, validate_arrangement
from .abc import compile_arrangement_abc
from .yue2 import compile_yue2_request, qwen_enrich_prompt


def render_arrangement(*args, **kwargs):
    """Load the optional waveform renderer only when a render is requested."""
    from .renderer import render_arrangement as _render
    return _render(*args, **kwargs)

__all__ = ["build_arrangement", "validate_arrangement", "compile_arrangement_abc", "compile_yue2_request", "qwen_enrich_prompt", "render_arrangement"]
