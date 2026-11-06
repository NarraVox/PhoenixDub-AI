"""Centralized logging utilities for style analyzer with real-time console output."""
import logging
from pathlib import Path


def setup_logging(project_path):
    """Configure both file and console logging with timestamps."""
    project = Path(project_path)
    
    # Configure logging once to avoid duplication
    logger = logging.getLogger("style_analyzer")
    logger.setLevel(logging.INFO)
    
    # Create handlers if not already configured
    handlers = []
    for handler in logger.handlers:
        if isinstance(handler, (logging.FileHandler, logging.StreamHandler)):
            handlers.append(handler)
            break
    
    if not handlers:
        # Console handler with timestamps
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler for detailed logs
        file_handler = logging.FileHandler(project / "analysis.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_stage_start(logger, stage_name):
    """Log the start of a processing stage."""
    logger.info("STAGE_START: %s", stage_name)


def log_stage_end(logger, stage_name, duration="auto"):
    """Log the completion of a processing stage."""
    if duration != "auto":
        logger.info("STAGE_END: %s (duration: %s)", stage_name, duration)


def log_gpu_info(logger, device_type, gpu_name=None):
    """Log GPU/CPU detection and availability."""
    if device_type == "gpu":
        if gpu_name:
            logger.info("DISPOSITIVO: GPU CUDA (%s)", gpu_name[:20])
        else:
            logger.info("DISPOSITIVO: GPU CUDA (disponivel)")
    else:
        logger.info("DISPOSITIVO: CPU")


def log_audio_info(logger, path, duration_seconds):
    """Log audio file information."""
    logger.info("ARQUIVO: %s (%.1fs)", path.name, duration_seconds)


def log_progress(logger, stage, fraction, total=None):
    """Log progress update without excessive output."""
    if fraction >= 0.95 or (total is None and fraction > 0.8):
        logger.info("PROGRESSO: %s (%d%%)" % (stage, int(fraction*100)) + 
                    (" (%d)" % total) if total else "")


def log_stems_generated(logger, target_names):
    """Log generated stems."""
    stems = ", ".join(target_names)
    logger.info("STEMES GERADOS: %s", stems)


def log_analysis_summary(logger, analysis_data):
    """Log a summary of the full analysis."""
    if "stem_origin" in analysis_data:
        logger.info("ORIGEM SEPARACAO: %s", analysis_data["stem_origin"])
    
    if "patterns" in analysis_data:
        total_patterns = len(analysis_data["patterns"])
        main_count = sum(1 for p in analysis_data["patterns"] if "MAIN" in p.get("candidate_type", ""))
        fill_count = sum(1 for p in analysis_data["patterns"] if p.get("type") == "FILL")
        break_count = sum(1 for p in analysis_data["patterns"] if p.get("type") == "BREAK")
        
        logger.info("RESUMO: %d patterns, %d MAIN, %d FILL, %d BREAK", 
                    total_patterns, main_count, fill_count, break_count)


def log_error(logger, exception):
    """Log an error with traceback."""
    import traceback
    logger.error("ERRO CRITICO:\n%s", traceback.format_exc())
