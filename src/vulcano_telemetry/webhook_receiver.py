"""Servidor HTTP Receptor de Webhooks utilizando FastAPI y Boto3 LocalStack."""

import logging
from fastapi import FastAPI, Request, HTTPException, status
from .webhook_crypto import verify_signature
from .core_sqs import get_sqs_client, produce_event
from .exceptions import WebhookSignatureError, WebhookTimestampError

logger = logging.getLogger("vulcano_engine")
app = FastAPI(title="Vulcano Webhook Receiver")

WEBHOOK_SECRET = "mi_clave_secreta_super_segura_vulcano_123"
QUEUE_URL = "http://localhost:4566/000000000000/vulcano-events-queue"

@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_webhook(request: Request):
    """
    Endpoint receptor de Webhooks:
    1. Lee raw body bytes (antes de llamar a .json()).
    2. Valida la firma HMAC y Timestamp.
    3. Responde HTTP 202 Accepted y encola en SQS.
    """
    raw_bytes = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature", "")

    try:
        verify_signature(WEBHOOK_SECRET, signature_header, raw_bytes)
    except (WebhookSignatureError, WebhookTimestampError) as err:
        logger.warning(f"Rechazado Webhook no autenticado: {err}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    payload = await request.json()
    client = get_sqs_client()
    msg_id = produce_event(client, QUEUE_URL, payload)

    logger.info(f"Webhook verificado y encolado exitosamente en SQS. MessageId: {msg_id}")
    return {"status": "accepted", "message_id": msg_id}