"""Exportação das correções e cópia organizada por jogo."""
import os
import shutil
import uuid
from nexus.correction_service import CorrectionError, local_file, write_json
from nexus.correction_game_output import game_destination, atomic_copy

def export_corrections(self, key, segment_id=None):
    with self.lock:
        folder, kind, segments = self.project(key)
        manifest = self.manifest(folder)
        if not manifest:
            raise CorrectionError("Salve ao menos uma correção antes de exportar.")
        for sid, info in manifest.items():
            _, _, seg = self.segment(key, sid)
            if info["fingerprint"] != self.fingerprint(folder, self.audio(folder, kind, seg)):
                raise CorrectionError("O projeto original mudou. Gere novamente as prévias das correções salvas.")
        output = folder / "_correcoes" / "exportacoes" / ("jogos" if kind == "games" else uuid.uuid4().hex[:12])
        output.mkdir(parents=True, exist_ok=True)
        game_folder = game_destination(self, folder) if kind == 'games' else None
        if kind == "games":
            for sid, info in manifest.items():
                if segment_id is not None and str(sid) != str(segment_id):
                    continue
                _, _, seg = self.segment(key, sid)
                name = self.audio(folder, kind, seg).name
                audio = local_file(folder, folder / info["path"])
                atomic_copy(audio, local_file(folder, output / name))
                if game_folder is not None:
                    atomic_copy(audio, local_file(self.uploads, game_folder / name))
            message = "Áudios corrigidos exportados. Use esta pasta na substituição ou no repack do jogo."
        else:
            self.export_video(folder, segments, manifest, output)
            message = "Nova cópia do vídeo exportada com as correções."
        write_json(output / "correcoes.json", manifest)
        if game_folder is not None:
            message = 'Correções salvas e copiadas para a pasta do jogo. Copie a pasta do personagem para o jogo.'
        return {"folder": str(game_folder or output), "corrections_folder": str(output),
                "game_folder": str(game_folder) if game_folder else None, "message": message}
