# -*- coding: utf-8 -*-
"""Regras de compatibilidade com TV para o conversor de mídia.

Decide se vale a pena recodificar um vídeo: se o arquivo já toca em TV
(H.264/HEVC) e a conversão deixaria o arquivo maior, não há ganho.
"""

# Codecs de vídeo que praticamente toda Smart TV decodifica.
TV_VIDEO_CODECS = {'h264', 'avc', 'avc1', 'hevc', 'h265'}

# Contêineres que as TVs abrem de forma confiável.
TV_CONTAINERS = {'.mp4', '.m4v'}


def is_tv_codec(codec: str) -> bool:
    return (codec or '').lower() in TV_VIDEO_CODECS


def is_tv_ready(info: dict) -> bool:
    """Arquivo já pronto para TV: contêiner MP4 com codec H.264/HEVC."""
    return (info.get('ext') or '').lower() in TV_CONTAINERS and is_tv_codec(info.get('codec'))


def plan_when_bigger(info: dict, est_mb: float, savings_pct: float):
    """Retorna um plano alternativo quando a conversão deixaria o arquivo maior.

    - Já pronto para TV (MP4 + H.264/HEVC): pula.
    - Codec compatível em outro contêiner (.mov, .mkv, .ts...): só troca o
      contêiner para MP4 (cópia direta, mesmo tamanho).
    - Codec incompatível (ProRes, MPEG-4/DivX, WMV, VP9...): retorna None e a
      recodificação segue, porque provavelmente não tocaria na TV.
    """
    codec = (info.get('codec') or '').lower()
    ext = (info.get('ext') or '').lower()
    orig_mb = info.get('size_mb', 0.0)
    label = info.get('resolution_label', '')
    growth = max(0.0, -savings_pct)

    if is_tv_ready(info):
        return {
            'action': 'skip',
            'orig_size_mb': orig_mb,
            'estimated_size_mb': est_mb,
            'savings_pct': savings_pct,
            'target_res_label': label,
            'target_codec': codec.upper(),
            'explanation': (f"⏭️ Pulado: o vídeo já é {ext.upper()} {codec.upper()} (compatível com TV) "
                            f"e a conversão o deixaria ~{growth:.0f}% mais pesado."),
        }
    if is_tv_codec(codec):
        return {
            'action': 'remux',
            'orig_size_mb': orig_mb,
            'estimated_size_mb': orig_mb,
            'savings_pct': 0.0,
            'target_res_label': label,
            'target_codec': f"{codec.upper()} (Cópia)",
            'explanation': (f"⚡ Só troca de formato ({ext.upper()} ➔ MP4) com cópia direta: recodificar "
                            f"deixaria o arquivo ~{growth:.0f}% mais pesado, e o codec {codec.upper()} já toca na TV."),
        }
    return None
