"""Validador forense de telemetría, formato JSON y descompresión Gzip."""

import gzip
import json

def test_log_gzip_decompression(tmp_path):
    """Verifica que los archivos .gz se descompriman y contengan JSON estructurado."""
    log_file = tmp_path / "forensic_sample.log.gz"
    sample_data = {
        "timestamp": "2026-10-31T20:00:00Z",
        "logger": "vulcano_engine",
        "level": "INFO",
        "message": "Transacción auditada con éxito",
        "trace_id": "trace_9981",
        "message_id": "sqs-msg-12345"
    }

    # Simular escritura comprimida en Gzip
    with gzip.open(log_file, "wb") as f_out:
        f_out.write((json.dumps(sample_data) + "\n").encode("utf-8"))

    # Simular lectura y descompresión forense
    with gzip.open(log_file, "rb") as f_in:
        line = f_in.readline().decode("utf-8")
        parsed = json.loads(line)

    assert parsed["level"] == "INFO"
    assert parsed["trace_id"] == "trace_9981"
    assert "timestamp" in parsed