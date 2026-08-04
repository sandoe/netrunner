import os
import time
import pika

target_ip = os.environ.get("TARGET_IP", "127.0.0.1")
queue_name = os.environ.get("AMQP_QUEUE", "test_queue")

print(f"Starting AMQP Test Subscriber connecting to {target_ip}:5672 on queue {queue_name}")

def connect():
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(target_ip,
                                           5672,
                                           '/',
                                           credentials)
    return pika.BlockingConnection(parameters)

def callback(ch, method, properties, body):
    print(f"Received message: {body.decode()}")

while True:
    try:
        connection = connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)

        channel.basic_consume(queue=queue_name,
                              auto_ack=True,
                              on_message_callback=callback)

        print("Waiting for messages...")
        channel.start_consuming()
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5s...")
        time.sleep(5)
