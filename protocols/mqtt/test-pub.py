import os
import time
import paho.mqtt.client as mqtt

broker_ip = os.environ.get("TARGET_IP", "127.0.0.1")
topic = os.environ.get("MQTT_TOPIC", "test/topic")

print(f"Starting Test Publisher connecting to {broker_ip} on topic {topic}")

client = mqtt.Client(client_id="test-publisher")
while True:
    try:
        client.connect(broker_ip, 1883, 60)
        break
    except Exception as e:
        print(f"Failed to connect to {broker_ip}: {e}. Retrying in 5s...")
        time.sleep(5)

client.loop_start()

count = 0
while True:
    message = f"Test message {count}"
    client.publish(topic, message)
    print(f"Published: {message} to {topic}")
    count += 1
    time.sleep(5)
