import sys
import uuid
import time
import json
from urllib.parse import parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

QUEUES = {
    "vulcano-events-queue": [],
    "vulcano-events-dlq": []
}

class SQSHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        target = self.headers.get("X-Amz-Target", "")

        path_parts = self.path.strip("/").split("/")
        qname = path_parts[-1] if path_parts and path_parts[-1] in QUEUES else "vulcano-events-queue"
        req_id = str(uuid.uuid4())

        # Protocolo AWS JSON (AmazonSQS.SendMessage, AmazonSQS.ReceiveMessage, etc.)
        if "application/x-amz-json" in content_type or target:
            action = target.split(".")[-1] if "." in target else ""
            data = json.loads(raw_body) if raw_body else {}

            self.send_response(200)
            self.send_header("Content-Type", "application/x-amz-json-1.0")
            self.send_header("x-amzn-RequestId", req_id)
            self.end_headers()

            if action == "CreateQueue":
                created_name = data.get("QueueName", "vulcano-events-queue")
                if created_name not in QUEUES:
                    QUEUES[created_name] = []
                res = {"QueueUrl": f"http://localhost:4566/000000000000/{created_name}"}
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif action == "SendMessage":
                msg_id = str(uuid.uuid4())
                receipt = f"{msg_id}##{time.time()}"
                body_content = data.get("MessageBody", "{}")
                QUEUES[qname].append({
                    "id": msg_id,
                    "body": body_content,
                    "receipt": receipt,
                    "attributes": data.get("MessageAttributes", {})
                })
                print(f"[SQS Local 4566] Evento encolado en '{qname}' | ID: {msg_id}")
                res = {
                    "MD5OfMessageBody": "mockmd5",
                    "MessageId": msg_id,
                    "messageId": msg_id,
                    "SequenceNumber": "0"
                }
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif action == "ReceiveMessage":
                messages = []
                if QUEUES.get(qname):
                    msg = QUEUES[qname][0]
                    messages.append({
                        "MessageId": msg["id"],
                        "messageId": msg["id"],
                        "ReceiptHandle": msg["receipt"],
                        "receiptHandle": msg["receipt"],
                        "MD5OfBody": "mockmd5",
                        "Body": msg["body"],
                        "body": msg["body"],
                        "Attributes": {},
                        "MessageAttributes": msg.get("attributes", {})
                    })

                res = {"Messages": messages, "messages": messages}
                self.wfile.write(json.dumps(res).encode("utf-8"))

            elif action == "DeleteMessage":
                receipt = data.get("ReceiptHandle", "")
                QUEUES[qname] = [m for m in QUEUES.get(qname, []) if m["receipt"] != receipt]
                print(f"[SQS Local 4566] Evento borrado con ReceiptHandle: {receipt[:15]}...")
                self.wfile.write(b"{}")

            else:
                self.wfile.write(b"{}")
            return

        # Protocolo Query / Form URL Encoded
        params = parse_qs(raw_body)
        action = params.get("Action", [""])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.send_header("x-amzn-RequestId", req_id)
        self.end_headers()

        ns = 'xmlns="http://queue.amazonaws.com/doc/2012-11-05/"'

        if action == "SendMessage":
            msg_body = params.get("MessageBody", ["{}"])[0]
            msg_id = str(uuid.uuid4())
            receipt = f"{msg_id}##{time.time()}"
            QUEUES[qname].append({"id": msg_id, "body": msg_body, "receipt": receipt, "attributes": {}})
            print(f"[SQS Local 4566] Evento encolado en '{qname}' | ID: {msg_id}")
            xml = f"""<SendMessageResponse {ns}><SendMessageResult><MD5OfMessageBody>mockmd5</MD5OfMessageBody><MessageId>{msg_id}</MessageId></SendMessageResult><ResponseMetadata><RequestId>{req_id}</RequestId></ResponseMetadata></SendMessageResponse>"""
            self.wfile.write(xml.encode("utf-8"))

        elif action == "ReceiveMessage":
            messages = []
            if QUEUES.get(qname):
                messages.append(QUEUES[qname][0])
            msgs_xml = "".join([f"""<Message><MessageId>{m['id']}</MessageId><ReceiptHandle>{m['receipt']}</ReceiptHandle><MD5OfBody>mockmd5</MD5OfBody><Body>{m['body']}</Body></Message>""" for m in messages])
            xml = f"""<ReceiveMessageResponse {ns}><ReceiveMessageResult>{msgs_xml}</ReceiveMessageResult><ResponseMetadata><RequestId>{req_id}</RequestId></ResponseMetadata></ReceiveMessageResponse>"""
            self.wfile.write(xml.encode("utf-8"))

        elif action == "DeleteMessage":
            receipt = params.get("ReceiptHandle", [""])[0]
            QUEUES[qname] = [m for m in QUEUES.get(qname, []) if m["receipt"] != receipt]
            print(f"[SQS Local 4566] Evento borrado con ReceiptHandle: {receipt[:15]}...")
            xml = f"""<DeleteMessageResponse {ns}><ResponseMetadata><RequestId>{req_id}</RequestId></DeleteMessageResponse>"""
            self.wfile.write(xml.encode("utf-8"))

        else:
            xml = f"""<Response {ns}><ResponseMetadata><RequestId>{req_id}</RequestId></ResponseMetadata></Response>"""
            self.wfile.write(xml.encode("utf-8"))

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 4566), SQSHandler)
    print(">>> Servidor SQS Local corriendo en http://localhost:4566")
    print(">>> Colas inicializadas: 'vulcano-events-queue' y 'vulcano-events-dlq'")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor SQS detenido.")