import json
import struct
import pika

from app.helpers.const import (
    RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASSWORD,
    RABBIT_QUEUE, HOST_PATH
)


def send_json_message(message:dict) -> None:
    """
    With a dict as argument, converts it to string and pushes it to the
    fn-ai queue
    """
    credentials = pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)
    parameters = pika.ConnectionParameters(host=RABBIT_HOST, port=RABBIT_PORT, credentials=credentials)
    connection = pika.BlockingConnection(parameters)

    channel = connection.channel()
    channel.queue_declare(queue=RABBIT_QUEUE, durable=True)
    dataset_file = f"{HOST_PATH}/fetched-data/{message.pop("file_name")}.csv"

    message["message"] = message.pop("query")

    json_bytes: bytes = json.dumps(message).encode()
    length_prefix: bytes = struct.pack('>I', len(json_bytes))
    file_contents: bytes = b"".join(open(dataset_file, "rb").readlines())

    channel.basic_publish('fnslm',
                        '/prompts',
                        length_prefix + json_bytes + file_contents,
                        pika.BasicProperties(content_type='application/octet-stream',
                                            delivery_mode=pika.DeliveryMode.Transient))

    connection.close()
