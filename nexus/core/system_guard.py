# -*- coding: utf-8 -*-
"""
NEXUS CORE :: SYSTEM RAM & VRAM SAFETY GUARD
Guardião de segurança pré-voo obrigatório (Regra 9 do AGENTS.md).
Monitora o consumo de memória RAM (16GB max) e VRAM (RTX 3050 6GB)
para impedir congelamentos e saturação de memória.
"""

import gc
import time
import psutil
import logging
import threading
import torch

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Limites de Segurança Rígidos
MAX_RAM_PERCENT_ALLOWED = 75.0  # Máximo de 75% de ocupação no pré-voo
CRITICAL_RAM_PERCENT = 82.0     # Ponto de corte imediato do Watchdog em tempo real
MIN_FREE_RAM_GB = 4.0           # Mínimo de 4GB de RAM livre no pré-voo
CRITICAL_MIN_FREE_RAM_GB = 2.5  # Mínimo absoluto para abortar o processo
MAX_PROCESS_RAM_GB = 3.5        # Máximo de 3.5GB consumido pelo processo atual


def emergency_cleanup():
    """Executa limpeza forçada instantânea de VRAM e RAM."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def check_system_safety(abort_on_risk: bool = True) -> bool:
    """
    Executa a checagem pré-voo de segurança de hardware.
    Retorna True se estiver seguro, ou levanta RuntimeError se houver risco de congelamento.
    """
    emergency_cleanup()

    mem = psutil.virtual_memory()
    total_ram_gb = mem.total / (1024 ** 3)
    free_ram_gb = mem.available / (1024 ** 3)
    used_percent = mem.percent

    proc = psutil.Process()
    proc_ram_gb = proc.memory_info().rss / (1024 ** 3)

    gpu_info = "N/A"
    if torch.cuda.is_available():
        gpu_allocated = torch.cuda.memory_allocated() / (1024 ** 2)
        gpu_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        gpu_info = f"{gpu_allocated:.1f}MB / {gpu_total:.1f}GB VRAM"

    logging.info(
        f"🛡️ [SAFETY GUARD] RAM: {used_percent:.1f}% usado ({free_ram_gb:.2f}GB livre de {total_ram_gb:.1f}GB) | "
        f"Processo: {proc_ram_gb:.2f}GB | GPU: {gpu_info}"
    )

    if used_percent > MAX_RAM_PERCENT_ALLOWED or free_ram_gb < MIN_FREE_RAM_GB:
        msg = (
            f"🚨 [ALERTA DE SEGURANÇA] RAM do sistema em nível crítico ({used_percent:.1f}% usado, {free_ram_gb:.2f}GB livre). "
            f"Execução bloqueada preventivamente para proteger o Windows de congelamentos."
        )
        logging.error(msg)
        if abort_on_risk:
            raise RuntimeError(msg)
        return False

    if proc_ram_gb > MAX_PROCESS_RAM_GB:
        msg = f"🚨 [ALERTA DE SEGURANÇA] Processo ultrapassou o teto seguro de RAM ({proc_ram_gb:.2f}GB > {MAX_PROCESS_RAM_GB}GB)."
        logging.error(msg)
        if abort_on_risk:
            raise RuntimeError(msg)
        return False

    return True


class SystemGuardWatchdog:
    """
    Sentinela em Segundo Plano (Watchdog):
    Monitora a RAM a cada 500ms durante a inferência.
    Dispara o corte de emergência automático se a RAM atingir nível crítico.
    """
    def __init__(self, check_interval_sec: float = 0.5, on_critical_abort=None):
        self.interval = check_interval_sec
        self.on_critical_abort = on_critical_abort
        self._running = False
        self._thread = None

    def _monitor_loop(self):
        while self._running:
            mem = psutil.virtual_memory()
            free_gb = mem.available / (1024 ** 3)
            used_pct = mem.percent

            if used_pct >= CRITICAL_RAM_PERCENT or free_gb <= CRITICAL_MIN_FREE_RAM_GB:
                logging.critical(
                    f"🚨🚨 [WATCHDOG KILL-SWITCH] RAM ATINGIU NÍVEL CRÍTICO: {used_pct:.1f}% ({free_gb:.2f}GB livre)! "
                    f"Acionando corte de emergência para proteger o Windows..."
                )
                emergency_cleanup()
                if self.on_critical_abort:
                    try:
                        self.on_critical_abort()
                    except Exception as e:
                        logging.error(f"Erro no callback de abort: {e}")
                self._running = False
                break

            time.sleep(self.interval)

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SystemGuardWatchdog")
            self._thread.start()
            logging.info("🛡️ [WATCHDOG] Sentinela de RAM em tempo real ATIVADO (Amostragem a cada 500ms).")

    def stop(self):
        if self._running:
            self._running = False
            logging.info("🛡️ [WATCHDOG] Sentinela de RAM desativado normalmente.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        emergency_cleanup()


if __name__ == "__main__":
    check_system_safety()
    with SystemGuardWatchdog():
        time.sleep(1)
