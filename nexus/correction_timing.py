"""Duração original do roteiro; nunca usa a dublagem existente como janela."""
import math


def positive(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value > 0 else None
    except (TypeError, ValueError):
        return None


def original_duration(segment, kind):
    if kind == 'games':
        duration = positive(segment.get('duration'))
        if duration is not None:
            return duration
    for start, end in [('start', 'end'), ('start_time', 'end_time')]:
        try:
            duration = positive(float(segment[end]) - float(segment[start]))
            if duration is not None:
                return duration
        except (TypeError, ValueError, KeyError):
            continue
    return None
