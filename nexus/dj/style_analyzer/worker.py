"""Standalone process: no imports of Nexus Core/model singletons. Logs to both file and console."""
import logging
import sys
import traceback
from pathlib import Path

from .pipeline import run
from .store import write_json


def main(root, project):
    project = Path(project)
    
    # Configure logging to output to both console AND file
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%H:%M:%S"
    
    logger = logging.getLogger("style_analyzer")
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    
    # Console handler (stdout - visible in CMD where worker runs)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt))
    logger.addHandler(console_handler)
    
    # File handler for persistent logs
    file_handler = logging.FileHandler(project / "analysis.log")
    file_handler.setFormatter(logging.Formatter(log_format, datefmt))
    logger.addHandler(file_handler)
    
    def progress(stage, fraction):
        write_json(project / "job_status.json", {"status": "running", "stage": stage, "fraction": fraction})

    try:
        result = run(root, project, progress)
        
        # Log completion to console
        print("TAREFA COMPLETADA")
        write_json(project / "job_status.json", {"status": "completed", "stage": "completed",
                                                 "fraction": 1, "cached": result.get("cached", False)})
        return 0
        
    except Exception as exc:
        # Log error to console and file
        logger.error("ERRO CRITICO:\n%s", traceback.format_exc())
        write_json(project / "job_status.json", {"status": "failed", "error": str(exc)})
        return 1
    finally:
        for handler in list(logger.handlers):
            try:
                handler.flush()
                handler.close()
            finally:
                logger.removeHandler(handler)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
