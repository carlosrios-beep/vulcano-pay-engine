# Vulcano Pay - Event Engine (SQS + Webhooks)

Plataforma de procesamiento asíncrono y tolerante a fallos para la recepción y re-emisión de notificaciones financieras mediante Webhooks y colas AWS SQS en LocalStack.

## 1. Arquitectura del Sistema

```mermaid
graph TD
    A[app_operator.py - CLI Entrypoint] -->|1. Sanitiza argumentos| B[sanitizer.py]
    A -->|2. Despacha evento HTTP POST| C[webhook_receiver.py - FastAPI]
    C -->|3. Valida raw bytes + HMAC-SHA256| D[webhook_crypto.py]
    C -->|4. HTTP 202 Accepted + Encola| E[core_sqs.py - LocalStack SQS]
    E -->|5. Long Polling Consumer| A
    A -->|6. Manejo concurrente de errores| F[except* - PEP 765]
    A -->|7. Registro asíncrono| G[logging_engine.py]
    G -->|8. Desacoplamiento no bloqueante| H[QueueHandler / QueueListener]
    H -->|9. Rotación y compresión atómica| I[vulcano_events.log.gz]