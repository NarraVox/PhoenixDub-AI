"""Processa as falas selecionadas com contagem global verificável."""
from nexus.correction_service import CorrectionError

def process_queue(self, key, segment_id=None, progress=None, snapshots=None):
    folder, kind, _ = self.project(key)
    pending = snapshots if snapshots is not None else [d["queued"] for d in self.drafts(folder).values()
               if d.get("queued") and d["queued"].get("status") != "done"
               and (segment_id is None or d["segment_id"] == segment_id)]
    pending = sorted(pending, key=lambda d: (d.get("queued_at", d["revision"]), d["revision"], d["segment_id"]))
    if not pending and not self.manifest(folder):
        raise CorrectionError("Edite e salve uma fala antes de começar.")
    failures = []
    completed = 0
    def report(message, current=None, stage='generating'):
        if progress:
            progress({'message': message, 'total': len(pending), 'completed': completed,
                      'failed': len(failures), 'current': current, 'stage': stage})
    for index, draft in enumerate(pending):
        report(f"Gerando: {draft['segment_id']}", draft['segment_id'])
        self.set_draft_status(folder, draft, status="running", error=None)
        try:
            # Uma interrupção após gerar a prévia não exige gastar GPU novamente.
            token = draft.get("preview_token")
            if token:
                _, info = self.preview_file(key, token)
            else:
                info = self.preview(key, draft["segment_id"], draft["text"])
                self.set_draft_status(folder, draft, preview_token=info["token"])
            self.apply(key, info["token"])
            self.set_draft_status(folder, draft, status="done", error=None)
            completed += 1
            timing = ''
            if info.get('generated_duration') is not None:
                timing = f" — {info['generated_duration']:.2f}s, velocidade {info['speed']:.2f}x"
                if info.get('overrun_seconds', 0) > .02:
                    timing += f"; excede o original em {info['overrun_seconds']:.2f}s (fala preservada)"
                self.set_draft_status(folder, draft, generated_duration=info['generated_duration'], speed=info['speed'])
            report(f"Fala concluída: {draft['segment_id']}{timing}", stage='saved')
        except Exception as exc:
            failures.append({"segment_id": draft["segment_id"], "error": str(exc)})
            self.set_draft_status(folder, draft, status="error", error=str(exc), preview_token=None)
            report(f"Falha em {draft['segment_id']}: {exc}", stage='error')
    if failures:
        return {"message": "Algumas falas falharam. As alterações e as falas concluídas estão salvas; clique em Começar para tentar as pendentes novamente.",
                "failures": failures, "queue": self.queue(key)}
    report("Exportando o vídeo corrigido..." if kind == "video" else "Exportando os áudios corrigidos...", stage='exporting')
    result = self.export(key, segment_id=segment_id)
    result["queue"] = self.queue(key)
    return result

