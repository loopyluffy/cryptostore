

import json
import logging
import time
import os

from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

# from aiokafka import AIOKafkaProducer
# from yapic import json
from uuid import uuid4

LOG = logging.getLogger('cryptostore')


class LoopyKafkaProducer:
    def __init__(self, ip='127.0.0.1', port=9092, group_id=None):
        self.ip = ip
        self.port = port
        self.producer = {}
        self.group_id = group_id if group_id else 'loopy' 
        # self.key = key if key else self.default_key

    async def __connect(self, key):
        if key not in self.producer:
            loop = asyncio.get_event_loop()
            self.producer[key] = AIOKafkaProducer(acks=0,
                                                  loop=loop,
                                                  bootstrap_servers=f'{self.ip}:{self.port}',
                                                  client_id=self.group_id)
            await self.producer[key].start()

    async def write(self, key, data: dict):
        await self.__connect(key)
        # topic = f"{self.key}-{data['exchange']}".lower()
        topic = f"{self.key}".lower()
        await self.producer.send_and_wait(topic, json.dumps(data).encode('utf-8'))


class LoopyAvroKafkaProducer(LoopyKafkaProducer):
    def __init__(self, ip='127.0.0.1', port=9092, schema_registry_ip='127.0.0.1', schema_registry_port=8081):
        assert isinstance(schema_registry_ip, str)
        assert isinstance(schema_registry_port, int)

        super().__init__(ip=ip, port=port)

        self.schema_registry_conf = {'url': f'http://{schema_registry_ip}:{schema_registry_port}'}
        self.schema = {}

    def set_schema(self, key, schema):
        self.schema[key] = schema

    def __connect(self, key):
        if key not in self.producer:
            if key not in self.schema and not self.schema[key]:
                return False
            
        # schema_registry_conf = {'url': f'{self.schema_registry_ip}:{self.schema_registry_port}'}
        schema_registry_client = SchemaRegistryClient(self.schema_registry_conf)

        avro_serializer = AvroSerializer(schema_str=self.schema[key],
                                            schema_registry_client=schema_registry_client)

        producer_conf = {'bootstrap.servers': f'{self.ip}:{self.port}',
                        'key.serializer': StringSerializer('utf_8'),
                        'value.serializer': avro_serializer}

        self.producer[key] = SerializingProducer(producer_conf)

        return True

    def write(self, key, data: dict):
        if not self.__connect(key):
            LOG.info('kafka producer connect failed...')
            return False

        # topic = f"{self.key}-{data['exchange']}".lower()
        topic = key.lower()
        # Serve on_delivery callbacks from previous calls to produce()
        # self.producer.poll(0.0)
        self.producer[key].produce(topic=topic, key=str(uuid4()), value=data)
        # self.producer.produce(topic=topic, key=str(uuid4()), value=json.dumps(data).encode('utf-8'))
                            #   on_delivery=delivery_report)
        self.producer[key].flush()

        return True





