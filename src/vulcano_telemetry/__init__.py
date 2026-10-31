"""Paquete de telemetría y procesamiento de eventos Vulcano Pay."""

from .exceptions import (
    VulcanoError,
    SQSConnectionError,
    CorruptedMessageError,
    WebhookSignatureError,
    WebhookTimestampError,
    WebhookDeliveryError,
)
from .sanitizer import (
    parse_queue_name,
    parse_wait_time,
    parse_webhook_url,
    parse_secret_key,
)
from .core_sqs import get_sqs_client, produce_event, consume_events, delete_event
from .webhook_crypto import generate_signature, verify_signature
from .logging_engine import AsyncJSONFormatter, setup_vulcano_logging

__all__ = [
    "VulcanoError",
    "SQSConnectionError",
    "CorruptedMessageError",
    "WebhookSignatureError",
    "WebhookTimestampError",
    "WebhookDeliveryError",
    "parse_queue_name",
    "parse_wait_time",
    "parse_webhook_url",
    "parse_secret_key",
    "get_sqs_client",
    "produce_event",
    "consume_events",
    "delete_event",
    "generate_signature",
    "verify_signature",
    "AsyncJSONFormatter",
    "setup_vulcano_logging",
]