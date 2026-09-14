"""Busca global nos roteiros de uploads, com aproximação por palavra."""
from difflib import SequenceMatcher
from functools import lru_cache
import re
import unicodedata
from nexus.correction_timing import original_duration


@lru_cache(maxsize=50000)
def normalize(text):
    text = unicodedata.normalize("NFKD", str(text).casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(
        char for char in text if not unicodedata.combining(char))))


@lru_cache(maxsize=50000)
def similarity(word, other):
    if word == other:
        return 1.0
    if abs(len(word) - len(other)) > max(1, len(word) // 3):
        return 0.0
    matcher = SequenceMatcher(None, word, other)
    return matcher.ratio() if matcher.quick_ratio() >= .72 else 0.0


def relevance(query, fields):
    if not query:
        return 1.0
    values = [normalize(field) for field in fields]
    if any(query in value for value in values):
        return 1.0
    ignored = {"a", "as", "o", "os", "de", "da", "do", "e", "um", "uma"}
    wanted = [word for word in query.split() if word not in ignored]
    if not wanted:
        return 0
    best = 0
    for value in values:
        words = value.split()
        if any(not any(similarity(word, other) >= (1 if len(word) < 3 else .72)
                       for other in words) for word in wanted):
            continue
        # Uma janela curta evita combinar palavras espalhadas numa fala longa.
        for start in range(len(words)):
            available = words[start:start + len(wanted) + 3]
            scores = []
            for word in wanted:
                candidates = [(similarity(word, other), i)
                              for i, other in enumerate(available)
                              if abs(len(word) - len(other)) <= max(1, len(word) // 3)]
                score, index = max(candidates, default=(0, -1))
                if score < (1 if len(word) < 3 else .72):
                    break
                scores.append(score)
                available.pop(index)
            if len(scores) == len(wanted):
                best = max(best, sum(scores) / len(scores) * .95)
    return best


def search_uploads(service, query="", offset=0, key=None, limit=40, original=None):
    projects = service.discover()
    if key:
        service.project(key)  # Valida o filtro antes de pesquisar.
        projects = [project for project in projects if project["id"] == key]
    query = normalize(query)
    matches = []
    for project in projects:
        folder, kind, segments = service.project(project["id"])
        saved, drafts = service.manifest(folder), service.drafts(folder)
        for seg in segments:
            if not isinstance(seg, dict) or "id" not in seg:
                continue
            sid = str(seg["id"])
            draft = drafts.get(sid, {})
            correction = saved.get(sid, {})
            source = str(seg.get("original_text") or seg.get("text") or "")
            if original is not None and normalize(source) != normalize(original):
                continue
            translated = str(correction.get("text") or seg.get("manual_edit_text")
                             or seg.get("text_pt") or seg.get("translated_text") or "")
            translated = draft.get("text", translated)
            score = relevance(query, [sid, seg.get("file_name", ""), source, translated])
            if not score:
                continue
            matches.append({"id": sid, "project_id": project["id"],
                            "project_name": project["name"], "kind": kind,
                            "original": source, "translated": translated,
                            "original_duration": original_duration(seg, kind),
                            "generated_duration": correction.get('generated_duration', correction.get('duration')),
                            "speed": correction.get('speed'),
                            "speaker": seg.get("speaker", ""), "start": seg.get("start"),
                            "end": seg.get("end"), "corrected": sid in saved,
                            "revision": draft.get("revision", 0),
                            "draft_status": draft.get("status"),
                            "queued_revision": draft.get("queued", {}).get("revision"),
                            "error": draft.get("error"), "preview_token": correction.get("token"),
                            "approximate": score < 1, "score": score})
    matches.sort(key=lambda item: -item["score"])
    return {"items": matches[offset:offset + limit if limit is not None else None], "total": len(matches),
            "kind": projects[0]["kind"] if key else "all", "projects_searched": len(projects)}
