# Módulo Core Unificado do Nexus (v2026.MODULAR.CONSOLIDATED)
import sys

# Se estiver rodando como executável compilado (Frozen), não carrega as IAs pesadas
# já que elas foram excluídas do executável e rodam externamente via python.exe
if getattr(sys, 'frozen', False):
    from nexus.core.utils import *
    modules_to_patch = ['utils']
else:
    from nexus.core.utils import *
    from nexus.core.vocals import *
    from nexus.core.diarization import *
    from nexus.core.whisper import *
    from nexus.core.whisper_loader import *
    from nexus.core.qwen_loader import *
    from nexus.core.tts_loader import *
    from nexus.core.model_loader import *
    from nexus.core.tts import *
    from nexus.core.translation import *
    from nexus.core.translation_utils import *
    from nexus.core.translation_api import *
    from nexus.core.translation_processors import *
    from nexus.core.translation_corrector import *
    from nexus.core.translation_sync import *
    from nexus.core.translation_maestro import *
    from nexus.core.orchestrator_jobs_games import *
    from nexus.core.orchestrator_jobs_core import *
    from nexus.core.orchestrator_routes import *
    
    modules_to_patch = [
        'utils', 'vocals', 'diarization', 'whisper', 'whisper_loader', 'qwen_loader', 
        'tts_loader', 'model_loader', 'tts', 'translation', 'translation_utils', 
        'translation_api', 'translation_processors', 'translation_corrector', 
        'translation_sync', 'translation_maestro', 'orchestrator_jobs_games', 
        'orchestrator_jobs_core', 'orchestrator_routes'
    ]

# Patch dinâmico de namespace para evitar NameErrors e importações circulares a nível de execução
core_module = sys.modules['nexus.core']
core_globals = {k: v for k, v in core_module.__dict__.items() if not k.startswith('__')}

for name in modules_to_patch:
    mod_name = f"nexus.core.{name}"
    if mod_name in sys.modules:
        mod_dict = sys.modules[mod_name].__dict__
        for k, v in core_globals.items():
            if k not in mod_dict:
                mod_dict[k] = v
