"""Compile a YuE2-native two-voice ABC score from an arrangement."""
import re

from .planning import validate_arrangement

_PITCHES = ("C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B")
_ABC_LENGTHS = (48, 32, 24, 16, 12, 8, 6, 4, 3, 2, 1)


def _bar_units(meter):
    """Return the measure length in L:1/32 units."""
    match = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", str(meter))
    if not match:
        raise ValueError(f"Métrica ABC inválida: {meter!r}")
    numerator, denominator = map(int, match.groups())
    if numerator < 1 or denominator < 1 or 32 * numerator % denominator:
        raise ValueError(f"Métrica não representável exatamente em L:1/32: {meter!r}")
    return 32 * numerator // denominator


def _abc_pitch(midi):
    if isinstance(midi, bool) or not isinstance(midi, int) or not 0 <= midi <= 127:
        raise ValueError("Notas precisam ser MIDI entre 0 e 127")
    octave, pitch = divmod(midi, 12)
    token = _PITCHES[pitch]
    if octave >= 6:
        return token.lower() + "'" * (octave - 6)
    return token + "," * max(0, 5 - octave)


def _bass_bar(events, units):
    """Encode bass attacks as one monophonic Ins line on the 1/32 grid."""
    by_unit = {}
    for event in events or []:
        step = int(event.get("step", 0))
        if 0 <= step < 16 and event.get("pitch_midi") is not None:
            unit = round(step * units / 16)
            by_unit.setdefault(unit, int(event["pitch_midi"]))
    tokens, cursor = [], 0

    def emit_rest(length):
        while length:
            part = next(value for value in _ABC_LENGTHS if value <= length)
            tokens.append("z" + str(part))
            length -= part

    def emit_note(pitch, length):
        parts = []
        while length:
            part = next(value for value in _ABC_LENGTHS if value <= length)
            parts.append(part)
            length -= part
        note = _abc_pitch(pitch)
        tokens.extend(note + str(part) + ("-" if i < len(parts) - 1 else "")
                      for i, part in enumerate(parts))

    for unit, pitch in sorted(by_unit.items()):
        if unit > cursor:
            emit_rest(unit - cursor)
        end = min([next_unit for next_unit in by_unit if next_unit > unit] + [units])
        length = max(1, end - unit)
        emit_note(pitch, length)
        cursor = end
    if cursor < units:
        emit_rest(units - cursor)
    return " ".join(tokens or ["z" + str(units)]) + " |"


def compile_arrangement_abc(arrangement):
    """Emit native YuE2 Vocal/Ins monophonic score; detailed grooves stay in JSON."""
    validate_arrangement(arrangement)
    meter = str(arrangement.get("meter", "4/4"))
    units = _bar_units(meter)
    key = (arrangement.get("harmony") or {}).get("key", "C")
    if not re.fullmatch(r"[A-G](?:#|b)?m?", str(key)):
        key = "C"
    tempo = int(round(float(arrangement["tempo_bpm"])))
    lines = ["X:1", f"T:{arrangement.get('name', 'Nexus arrangement')}",
             f"M:{meter}", "L:1/32",
             f"Q:1/4={tempo}",
             'V: Vocal clef=treble name="Vocal"',
             'V: Ins clef=bass name="Ins"', f"K:{key}"]
    melody = arrangement.get("melody_by_bar") or []
    vocal_bars, ins_bars = [], []
    global_bar = 0
    section_blocks = []
    for section in arrangement["sections"]:
        perf = section.get("performance_by_bar", [])
        section_vocal, section_ins = [], []
        for offset, harmony in enumerate(section["harmony_by_bar"]):
            chord = harmony.get("chord") if isinstance(harmony, dict) else str(harmony)
            if not isinstance(chord, str) or not re.fullmatch(r"[A-G](?:#|b)?(?:m|dim|aug|sus2|sus4)?\d{0,2}", chord):
                raise ValueError(f"Acorde ABC inválido: {chord!r}")
            tokens = [f'"{chord}"']
            item = melody[global_bar] if global_bar < len(melody) else []
            used = 0
            for note in item:
                if not isinstance(note, dict):
                    raise ValueError("Cada nota precisa de pitch e duration_eighths")
                length = note.get("duration_eighths", 1)
                if isinstance(length, bool) or not isinstance(length, int) or length < 1:
                    raise ValueError("duration_eighths precisa ser inteiro positivo")
                units_note = length * 4
                used += units_note
                tokens.append(_abc_pitch(note.get("pitch")) + str(units_note))
            if used > units:
                raise ValueError("A melodia excede a duração do compasso")
            if used < units:
                tokens.append("z" + str(units - used))
            section_vocal.append(" ".join(tokens) + " |")
            bar_perf = perf[offset] if offset < len(perf) else {}
            section_ins.append(_bass_bar(bar_perf.get("bass", []), units))
            global_bar += 1
        section_blocks.append((section["type"], section_vocal, section_ins))
    # The native exporter groups up to four measures per section block, first
    # Vocal then Ins. Use only the structural comments in YuE2's documented dialect.
    comment_for = {"INTRO": "verse", "MAIN A": "verse", "MAIN B": "chorus",
                   "FILL A": "bridge", "FILL B": "bridge", "BREAK": "bridge",
                   "ENDING": "interlude"}
    out = []
    for section_type, vocals, instruments in section_blocks:
        comment = comment_for.get(section_type)
        for start in range(0, len(vocals), 4):
            if comment:
                out.append(f"% {comment}")
            out.append("[V: Vocal] " + " ".join(vocals[start:start + 4]))
            out.append("[V: Ins] " + " ".join(instruments[start:start + 4]))
    return "\n".join(lines + [""] + out) + "\n"
