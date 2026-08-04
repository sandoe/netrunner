import os
import time
import paho.mqtt.client as mqtt

broker_ip = os.environ.get("TARGET_IP", "127.0.0.1")
topic = os.environ.get("MQTT_TOPIC", "test/topic")

def on_connect(client, userdata, flags, rc):
    print(f"Connected to {broker_ip} with result code {rc}")
    client.subscribe(topic)
    print(f"Subscribed to topic: {topic}")

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")

print(f"Starting Test Subscriber connecting to {broker_ip} on topic {topic}")

client = mqtt.Client(client_id="test-subscriber")
client.on_connect = on_connect
client.on_message = on_message

while True:
    try:
        client.connect(broker_ip, 1883, 60)
        break
    except Exception as e:
        print(f"Failed to connect to {broker_ip}: {e}. Retrying in 5s...")
        time.sleep(5)

client.loop_forever()
