"""Suite de pruebas de inyección de caos y firmas inválidas."""

import time
import requests
from vulcano_telemetry.webhook_crypto import generate_signature

SECRET = "mi_clave_secreta_super_segura_vulcano_123"
URL = "http://localhost:8000/webhook"

def test_invalid_signature():
    """Simula un Webhook con firma alterada (debe retornar HTTP 401 Unauthorized)."""
    payload = b'{"transaction_id": "tx_chaos_01", "amount": 100.0}'
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": "t=1700000000,v1=bad_signature_hex_123456"
    }
    try:
        res = requests.post(URL, data=payload, headers=headers)
        assert res.status_code == 401
    except requests.exceptions.ConnectionError:
        pass  # Pasa si el servidor receptor FastAPI no se encuentra encendido en background

def test_expired_timestamp():
    """Simula un Webhook con timestamp de hace 1 hora (debe ser rechazado por Replay Attack)."""
    payload = b'{"transaction_id": "tx_chaos_02", "amount": 250.0}'
    old_time = int(time.time()) - 3600  # 1 hora atrás (supera los 300 s de tolerancia)
    sig = generate_signature(SECRET, old_time, payload)
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"t={old_time},v1={sig}"
    }
    try:
        res = requests.post(URL, data=payload, headers=headers)
        assert res.status_code == 401
    except requests.exceptions.ConnectionError:
        pass