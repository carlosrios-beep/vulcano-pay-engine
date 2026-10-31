"""Punto de entrada CLI ejecutable de Vulcano Pay."""

import argparse
import time
import requests
from vulcano_telemetry.sanitizer import (
    parse_queue_name,
    parse_wait_time,
    parse_webhook_url,
    parse_secret_key,
)
from vulcano_telemetry.core_sqs import get_sqs_client, consume_events, delete_event
from vulcano_telemetry.webhook_crypto import generate_signature
from vulcano_telemetry.logging_engine import setup_vulcano_logging
from vulcano_telemetry.exceptions import (
    SQSConnectionError,
    WebhookSignatureError,
    WebhookTimestampError,
    WebhookDeliveryError,
)

logger = setup_vulcano_logging()

def build_parser() -> argparse.ArgumentParser:
    """Configura el analizador de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(prog="VulcanoCLI", description="Motor de Eventos SQS y Webhooks HMAC")
    parser.add_argument("-q", "--queue", type=parse_queue_name, default="vulcano-events-queue", help="Nombre de la cola SQS")
    parser.add_argument("-w", "--wait-time", type=parse_wait_time, default=10, help="Tiempo de Long Polling (1-20s)")
    parser.add_argument("--url", type=parse_webhook_url, default="http://localhost:8000/webhook", help="URL del Webhook Receptor")
    parser.add_argument("--secret", type=parse_secret_key, default="mi_clave_secreta_super_segura_vulcano_123", help="Clave secreta HMAC")
    parser.add_argument("--mode", choices=["send-webhook", "start-dispatcher"], default="send-webhook", help="Modo operativo")
    return parser

def dispatch_webhook(target_url: str, secret: str, payload_bytes: bytes) -> requests.Response:
    """Firma el payload con HMAC-SHA256 y realiza el envío HTTP POST inyectando X-Webhook-Signature."""
    timestamp = int(time.time())
    signature = generate_signature(secret, timestamp, payload_bytes)
    header_val = f"t={timestamp},v1={signature}"

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": header_val
    }
    response = requests.post(target_url, data=payload_bytes, headers=headers)
    if response.status_code not in (200, 202):
        raise WebhookDeliveryError(f"Fallo en la entrega del Webhook: HTTP {response.status_code}")
    return response

def send_test_webhook(target_url: str, secret: str):
    """Envía un webhook de prueba firmado hacia el receptor local."""
    payload = '{"transaction_id": "tx_9981", "amount": 350.00, "status": "COMPLETED"}'
    response = dispatch_webhook(target_url, secret, payload.encode("utf-8"))
    logger.info(f"Respuesta del receptor Webhook HTTP {response.status_code}: {response.json()}")

def run_dispatcher(queue_name: str, wait_time: int, secret: str, url: str):
    """Consume eventos de LocalStack SQS y re-emite webhooks firmados a destinos finales."""
    sqs = get_sqs_client()
    queue_url = f"http://localhost:4566/000000000000/{queue_name}"
    logger.info("Iniciando despachador SQS -> Webhooks...")
    
    events = consume_events(sqs, queue_url, wait_time=wait_time)
    for event in events:
        payload_bytes = str(event["body"]).replace("'", '"').encode("utf-8")
        dispatch_webhook(url, secret, payload_bytes)
        delete_event(sqs, queue_url, event["receipt_handle"])
        logger.info(f"Evento {event['message_id']} despachado y eliminado de SQS.")

def main():
    parser = build_parser()
    args = parser.parse_args()
    logger.info(f"Iniciando VulcanoCLI en modo '{args.mode}'")

    try:
        if args.mode == "send-webhook":
            send_test_webhook(args.url, args.secret)
        elif args.mode == "start-dispatcher":
            run_dispatcher(args.queue, args.wait_time, args.secret, args.url)

    # Manejo de excepciones concurrentes con except* (Python 3.14 / PEP 765)
    except* WebhookSignatureError as group:
        logger.error(f"Errores de firma HMAC ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    except* WebhookTimestampError as group:
        logger.error(f"Errores de timestamp/replay ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    except* SQSConnectionError as group:
        logger.error(f"Errores de comunicación con SQS LocalStack ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    except* WebhookDeliveryError as group:
        logger.error(f"Errores de re-emisión de Webhooks ({len(group.exceptions)}):")
        for exc in group.exceptions:
            logger.error(f"  • {exc}")
    finally:
        # Apagado ordenado cumpliendo PEP 765 (prohibido return, break o continue)
        logger.info("Liberando recursos de observabilidad...")
        if hasattr(logger, "listener") and logger.listener:
            logger.listener.stop()

if __name__ == "__main__":
    main()