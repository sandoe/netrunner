import os
import msgpack
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

REDPANDA_BROKERS = os.getenv("REDPANDA_BROKERS", "127.0.0.1:9092")


async def get_producer():
    producer = AIOKafkaProducer(
        bootstrap_servers=REDPANDA_BROKERS,
        value_serializer=lambda v: msgpack.packb(v, use_bin_type=True),
    )
    await producer.start()
    return producer


async def get_consumer(topic: str, group_id: str = "nexus-group"):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=REDPANDA_BROKERS,
        group_id=group_id,
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
    )
    await consumer.start()
    return consumer
