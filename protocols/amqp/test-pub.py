import os
import time
import pika

target_ip = os.environ.get("TARGET_IP", "127.0.0.1")
queue_name = os.environ.get("AMQP_QUEUE", "test_queue")

print(f"Starting AMQP Test Publisher connecting to {target_ip}:5672 on queue {queue_name}")

def connect():
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(target_ip,
                                           5672,
                                           '/',
                                           credentials)
    return pika.BlockingConnection(parameters)

count = 0
while True:
    try:
        connection = connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue_name)

        while True:
            message = f"Test message {count}"
            channel.basic_publish(exchange='',
                                  routing_key=queue_name,
                                  body=message)
            print(f"Published: {message} to {queue_name}")
            count += 1
            time.sleep(5)

    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5s...")
        time.sleep(5)
