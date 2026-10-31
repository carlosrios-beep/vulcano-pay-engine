"""Excepciones semánticas personalizadas para el proyecto Vulcano Pay (SQS + Webhooks)."""

class VulcanoError(Exception):
    """Excepción base para todos los errores del ecosistema Vulcano (hereda de Exception)."""
    pass

# Excepciones de dominio SQS
class SQSConnectionError(VulcanoError):
    """Lanzada ante fallos de comunicación con AWS SQS / LocalStack."""
    pass

class QueueTimeoutError(VulcanoError):
    """Lanzada ante timeouts de espera en la cola SQS."""
    pass

class CorruptedMessageError(VulcanoError):
    """Lanzada cuando el cuerpo del mensaje SQS no es un JSON válido."""
    pass

# Excepciones de dominio Webhooks
class WebhookSignatureError(VulcanoError):
    """Lanzada cuando la firma criptográfica HMAC-SHA256 es inválida o ausente."""
    pass

class WebhookTimestampError(VulcanoError):
    """Lanzada cuando el timestamp del Webhook está fuera de tolerancia (Replay Attack)."""
    pass

class WebhookDeliveryError(VulcanoError):
    """Lanzada cuando el envío HTTP del Webhook falla tras reintentos."""
    pass