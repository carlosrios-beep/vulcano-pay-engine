"""Cliente Boto3 y operaciones de mensajería SQS con soporte para LocalStack."""

import json
import logging
import boto3
from botocore.exceptions import ClientError
from .exceptions import SQSConnectionError, CorruptedMessageError

logger = logging.getLogger("vulcano_engine")

def get_sqs_client(endpoint_url: str = "http://localhost:4566"):
    """Crea una instancia del cliente Boto3 SQS configurada para LocalStack."""
    return boto3.client(
        "sqs",
        endpoint_url=endpoint_url,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

def produce_event(sqs_client, queue_url: str, event_data: dict, trace_id: str = "N/A", event_topic: str = "payment.processed") -> str:
    """Publica un evento estructurado en la cola SQS agregando MessageAttributes."""
    try:
        payload = json.dumps(event_data)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=payload,
            MessageAttributes={
                "TraceId": {"DataType": "String", "StringValue": trace_id},
                "EventTopic": {"DataType": "String", "StringValue": event_topic},
                "Source": {"DataType": "String", "StringValue": "VulcanoWebhookEngine"}
            }
        )
        msg_id = (
            response.get("MessageId")
            or response.get("messageId")
            or response.get("ResponseMetadata", {}).get("RequestId")
            or "N/A"
        )
        logger.info(f"Evento publicado en SQS. MessageId: {msg_id}", extra={"message_id": msg_id})
        return msg_id
    except ClientError as err:
        sqs_err = SQSConnectionError("Error al enviar mensaje a AWS SQS LocalStack.")
        sqs_err.add_note(f"QueueUrl: {queue_url}")
        raise sqs_err from err

def consume_events(sqs_client, queue_url: str, wait_time: int = 10, max_messages: int = 5, visibility_timeout: int = 30):
    """Consume mensajes de SQS mediante Long Polling."""
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=visibility_timeout,
            MessageAttributeNames=["All"]
        )
        messages = response.get("Messages", []) or response.get("messages", [])
        processed = []
        for msg in messages:
            try:
                body = json.loads(msg["Body"]) if "Body" in msg else json.loads(msg["body"])
                processed.append({
                    "receipt_handle": msg.get("ReceiptHandle") or msg.get("receiptHandle"),
                    "message_id": msg.get("MessageId") or msg.get("messageId"),
                    "body": body,
                    "attributes": msg.get("MessageAttributes", {})
                })
            except (json.JSONDecodeError, KeyError) as err:
                corrupt_err = CorruptedMessageError(f"Mensaje SQS corrupto ID {msg.get('MessageId', 'unknown')}")
                raise corrupt_err from err
        return processed
    except ClientError as err:
        sqs_err = SQSConnectionError("Error en recepción de mensajes SQS.")
        sqs_err.add_note(f"QueueUrl: {queue_url}")
        raise sqs_err from err

def delete_event(sqs_client, queue_url: str, receipt_handle: str) -> None:
    """Elimina explícitamente un mensaje procesado de la cola SQS."""
    try:
        sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except ClientError as err:
        sqs_err = SQSConnectionError("Error al eliminar mensaje de SQS.")
        sqs_err.add_note(f"ReceiptHandle: {receipt_handle}")
        raise sqs_err from err