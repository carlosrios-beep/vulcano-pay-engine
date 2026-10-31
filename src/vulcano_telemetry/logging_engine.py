"""Engine de observabilidad con formato JSON, QueueHandler y compresión Gzip."""

import gzip
import json
import logging
import logging.handlers
import os
import queue
import shutil
from datetime import datetime, timezone

class AsyncJSONFormatter(logging.Formatter):
    """Formateador JSON estructurado conforme a ISO 8601 UTC."""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "process_id": record.process,
            "thread_name": record.threadName
        }
        if hasattr(record, "message_id"):
            log_data["message_id"] = record.message_id
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        # Serialización de excepciones y notas asociadas (PEP 765 / ExceptionGroup)
        if record.exc_info:
            exc_type, exc_val, _ = record.exc_info
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "details": self.formatException(record.exc_info)
            }
            if hasattr(exc_val, "__notes__"):
                log_data["exception"]["notes"] = getattr(exc_val, "__notes__")

        return json.dumps(log_data, ensure_ascii=False)

def gzip_namer(default_name: str) -> str:
    """Añade la extensión .gz al archivo rotado."""
    return default_name + ".gz"

def gzip_rotator(source: str, dest: str) -> None:
    """Comprime de forma atómica el archivo de log a gzip."""
    with open(source, "rb") as f_in:
        with gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    os.remove(source)

def setup_vulcano_logging(log_filename: str = "vulcano_events.log"):
    """Configura el pipeline de logging desacoplado no bloqueante con QueueHandler y QueueListener."""
    log_queue = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(log_queue)

    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(AsyncJSONFormatter())
    file_handler.namer = gzip_namer
    file_handler.rotator = gzip_rotator

    listener = logging.handlers.QueueListener(log_queue, file_handler)
    listener.start()

    logger = logging.getLogger("vulcano_engine")
    logger.setLevel(logging.INFO)
    logger.addHandler(queue_handler)
    logger.listener = listener
    return logger