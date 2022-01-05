

import json
import logging
import time
import os

from confluent_kafka.admin import AdminClient
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import StringDeserializer

from cryptofeed.defines import L2_BOOK, L3_BOOK, TRADES, TICKER, FUNDING, OPEN_INTEREST, BALANCES, POSITIONS, ORDER_INFO

from cryptostore.engines import StorageEngines
from cryptostore.aggregator.cache import Cache
from cryptostore.aggregator.kafka import Kafka

LOG = logging.getLogger('cryptostore')


class LoopyKafka(Kafka):
    def __init__(self, ip, port, group_id=None, flush=False):
        super().__init__(ip, port, flush)
        self.group_id = group_id if group_id else 'loopy' 
        # self.group_ids = {}

    def _conn(self, key):
        if key not in self.conn:
            client = AdminClient({'bootstrap.servers': f"{self.ip}:{self.port}"})    
            topic_metadata = client.list_topics()
            if topic_metadata.topics.get(key) is None:
                return None

            self.ids[key] = None
            # if key not in self.group_ids:
            #     self.group_ids[key] = f'{self.group_id}-{key}' 
            kafka = StorageEngines.confluent_kafka
            consumer_conf = {
                'bootstrap.servers': f"{self.ip}:{self.port}",
                #  'client.id': f'loopyquant_strategy-{key}',
                #  'group.id': f'{self.group_id}-{key}',
                'client.id': self.group_id,
                'group.id': self.group_id,
                # 'max.poll.interval.ms': 3000000,
                #  to read the message from latest @logan
                'default.topic.config': {
                    'auto.offset.reset': 'latest', 
                    'enable.auto.commit': False
                }
            }
            self.conn[key] = kafka.Consumer(consumer_conf)
            # self.conn[key].subscribe([key])
            # to read lastest 
            self.conn[key].subscribe([key], on_assign=self._on_assign)
            # to offset latest... @logan
            # self.conn[key].subscribe([key], on_assign=seek_to_end)
            # last_offset = self.conn[key].end_offsets([kafka.TopicPartition(key, 0)])[0]
            # self.conn[key].seek_to_end([kafka.TopicPartition(key, 0)])
            # last_offset -= 1
            # LOG.info(f'last_offset: {last_offset}')
            # self._conn(key).commit(last_offset)

        return self.conn[key]

    def _on_assign(self, consumer, partitions):
        if partitions:
            # set offset for topics
            topic = partitions[0].topic
            # LOG.info(f"kafka consumer on_assign [{topic}]")
            offset = 0
            # feed = [L2_BOOK, L3_BOOK, TRADES, TICKER, FUNDING, OPEN_INTEREST, BALANCES, POSITIONS, ORDER_INFO]
            feeds = [BALANCES, POSITIONS, 'view_macd_signal', 'view_atr']
            if any(feed in topic for feed in feeds):
                offset = 10

            if offset > 0:
                # get offset tuple from the first partition
                first_offset, last_offset = consumer.get_watermark_offsets(partitions[0])
                # position [1] being the last index
                read_offset = last_offset - offset
                if read_offset >= first_offset:
                    partitions[0].offset = last_offset - offset
                    consumer.assign(partitions)
                # LOG.info(f"kafka consumer on_assign [first_offset: {first_offset}, latest_offset: {last_offset}, read_offset: {read_offset}]")

    def read(self, topic_key, feed, exchange=None, latest_offset=False):
        if exchange:
            key = f'{topic_key}-{feed}-{exchange}'.lower()
        else:
            key = f'{topic_key}-{feed}'.lower()

        data = self._conn(key).consume(1000000, timeout=0.5)

        # LOG.info(f'LoopyKafka Read Topic: {key}')
        # if len(data) > 0:
        #     LOG.info("%s: Read %d messages from Kafka", key, len(data))
            
        ret = []

        for message in data:
            self.ids[key] = message
            msg = message.value().decode('utf8')
            try:
                update = json.loads(msg)
            except Exception:
                if 'Subscribed topic not available' in msg:
                    return ret
            if feed in {L2_BOOK, L3_BOOK}:
                update = book_flatten(update, update['timestamp'], update['delta'], update['receipt_timestamp'])
                ret.extend(update)
            elif feed in {TRADES, TICKER, FUNDING, OPEN_INTEREST, BALANCES, POSITIONS, ORDER_INFO}:
                ret.append(update)
            elif feed in {'view_grid_safety', 'view_macd_signal', 'view_atr'}:
                ret.append(update['payload'])

        if latest_offset == True and self.ids[key] is not None:
            kafka = StorageEngines['confluent_kafka.admin']
            current_offset, latest_offset = self._conn(key).get_watermark_offsets(kafka.TopicPartition(key, 0))
            read_offset = self.ids[key].offset()
            # if read_offset is None or latest_offset is None or read_offset < latest_offset - 1:
            if read_offset is None or latest_offset is None or read_offset < latest_offset - 10:
                LOG.info(f'{key}: check to consume from latest, read_offset: {read_offset}, latest_offset:{latest_offset}')
                return []
            # else:
            #     LOG.info("%s: Read %d messages from Kafka", key, len(data))
            #     LOG.info(f'{key}: check to cosume from latest, read_offset: {read_offset}, latest_offset:{latest_offset}')

        # LOG.info(f'return messages: {feed}: {ret}')
        return ret

    def delete(self, topic_key, feed, exchange=None):
        # if exchange:
        #     key = f'{topic_key}-{feed}-{exchange}'.lower()
        # else:
        #     key = f'{topic_key}-{feed}'.lower()
        # # LOG.info("%s: Committing offset %d", key, self.ids[key].offset())
        # self._conn(key).commit(message=self.ids[key])
        # self.ids[key] = None

        # try not to commit to read from latest offset (with 'auto.offset.reset': 'latest')
        return

    def reset_latest(self, topic_key, feed, exchange=None):
        kafka = StorageEngines.confluent_kafka
        if exchange:
            key = f'{topic_key}-{feed}-{exchange}'.lower()
        else:
            key = f'{topic_key}-{feed}'.lower()
        if key not in self.conn:
            self.ids[key] = None
            kafka = StorageEngines.confluent_kafka
            self.conn[key] = kafka.Consumer({'bootstrap.servers': f"{self.ip}:{self.port}",
                                            #  'client.id': f'grid_protection_strategy-{key}',
                                             'client.id': self.group_id,
                                             'enable.auto.commit': False,
                                            #  'group.id': f'loopyluffy-{key}',
                                             'group.id': self.group_id,
                                             'max.poll.interval.ms': 3000000,
                                            #  to read the message from latest @logan
                                             "auto.offset.reset" : "latest"})
            self.conn[key].subscribe([key], on_assign=self._reset_offsets)

    def _reset_offsets(self, consumer, partitions):
        key = partitions[0].topic 
        start_offset = partitions[0].offset
        first_offset, stop_offset = consumer.get_watermark_offsets(partitions[0])
        LOG.info(f'on_assign: partions: {partitions}')
        LOG.info(f'topic: {key}, current_offset: {start_offset}, latest_offset:{stop_offset}')
        if start_offset == -1 or start_offset == -1001:
            return 

        offset_diff = stop_offset - start_offset
        LOG.info(f'topic: {key}, offset_diff: {offset_diff}')
        if offset_diff <= 0:
            return 

        data = consumer.consume(offset_diff, timeout=0.5)
        if len(data) > 0:
            LOG.info("%s: Read %d messages from Kafka", key, len(data))
        else:
            LOG.info('why?...???')
            return

        for message in data:
            self.ids[key] = message
        LOG.info("%s: Committing offset %d", key, self.ids[key].offset())
        consumer.commit(message=self.ids[key])
        self.ids[key] = None


class LoopyAvroKafka(LoopyKafka):
    def __init__(self, ip, port, schema_registry_ip, schema_registry_port, group_id=None, flush=False):
        assert isinstance(schema_registry_ip, str)
        assert isinstance(schema_registry_port, int)

        super().__init__(ip, port, group_id, flush)

        self.schema_registry_conf = {'url': f'http://{schema_registry_ip}:{schema_registry_port}'}

    def _conn(self, key):
        if key not in self.conn:
            client = AdminClient({'bootstrap.servers': f"{self.ip}:{self.port}"})    
            topic_metadata = client.list_topics()
            if topic_metadata.topics.get(key) is None:
                return None

            schema_str = None
            # LOG.info(key)
            if key.find(ORDER_INFO) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "OrderInfo",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "id", "type": "string"},
                        {"name": "account", "type": "string"},
                        {"name": "position", "type": "string"},
                        {"name": "side", "type": "string"},
                        {"name": "status", "type": "string"},
                        {"name": "type", "type": "string"},
                        {"name": "price", "type": "float"},
                        {"name": "condition_price", "type": "float"},
                        {"name": "amount", "type": "float"},
                        {"name": "remaining", "type": "float"},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
                # LOG.info(schema_str)
            elif key.find(POSITIONS) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "Position",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "account", "type": "string"},
                        {"name": "id", "type": "string"},
                        {"name": "margin_type", "type": "string", "default": ""},
                        {"name": "side", "type": "string", "default": ""},
                        {"name": "entry_price", "type": "float", "default": 0},
                        {"name": "amount", "type": "float", "default": 0},
                        {"name": "unrealised_pnl", "type": "float", "default": 0},
                        {"name": "cum_pnl", "type": "float", "default": 0},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
            elif key.find(BALANCES) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "Balance",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "currency", "type": "string"},
                        {"name": "account", "type": "string"},
                        {"name": "balance", "type": "float"},
                        {"name": "cw_balance", "type": "float"},
                        {"name": "changed", "type": "float"},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
            elif key.find(FUNDING) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "Funding",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "mark_price", "type": "float"},
                        {"name": "rate", "type": "float"},
                        {"name": "next_funding_time", "type": "float", "default": 0},
                        {"name": "predicted_rate", "type": "float"},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
            elif key.find(TICKER) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "Ticker",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "bid", "type": "float"},
                        {"name": "ask", "type": "float"},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
            elif key.find(TRADES) >= 0:
                schema_str = """
                {
                    "namespace": "loopyluffy.serialization.avro",
                    "name": "Trade",
                    "type": "record",
                    "fields": [
                        {"name": "exchange", "type": "string"},
                        {"name": "symbol", "type": "string"},
                        {"name": "price", "type": "float"},
                        {"name": "amount", "type": "float"},
                        {"name": "side", "type": "string"},
                        {"name": "id", "type": "string", "default": ""},
                        {"name": "type", "type": "string", "default": ""},
                        {"name": "timestamp", "type": "float"},
                        {"name": "receipt_timestamp", "type": "float"}
                    ]
                }
                """
            else:
                return None

            schema_registry_client = SchemaRegistryClient(self.schema_registry_conf)
            avro_deserializer = AvroDeserializer(schema_str=schema_str,
                                                 schema_registry_client=schema_registry_client)
            string_deserializer = StringDeserializer('utf_8')
            # consumer_conf = {'bootstrap.servers': f"{self.ip}:{self.port}",
            #                 'key.deserializer': string_deserializer,
            #                 'value.deserializer': avro_deserializer,
            #                 # 'group.id': f'{self.group_id}-{key}',
            #                 'group.id': self.group_id,
            #                 'auto.offset.reset': "latest"}
            consumer_conf = {
                'bootstrap.servers': f"{self.ip}:{self.port}",
                'key.deserializer': string_deserializer,
                'value.deserializer': avro_deserializer,
                'client.id': self.group_id,
                'group.id': self.group_id,
                'default.topic.config': {
                    'auto.offset.reset': 'latest', 
                    'enable.auto.commit': False
                }
            }
            self.conn[key] = DeserializingConsumer(consumer_conf)

            # try:
            # self.conn[key].subscribe([key])
            # to read lastest 
            self.conn[key].subscribe([key], on_assign=super()._on_assign)
        #     except KafkaException as e:
        #         LOG.info(f"Kafka DeserializingConsumer subscribe exception: {str(e)}")
        #         pass
        # elif self.conn[key].need_assign_:
        #     try:
        #         self.conn[key].subscribe([key])
        #     except KafkaException as e:
        #         LOG.info(f"Kafka DeserializingConsumer subscribe exception: {str(e)}")
        #         pass

        # if self.conn[key].need_assign_:
        #     return None
        # else:
        return self.conn[key]

    def _consume(self, key, timeout=1.0):
        ret = []
        if self._conn(key) is None:
            return ret

        interval_start = time.time()
        while True:
            try:
                interval = time.time() - interval_start
                if interval >= timeout:
                    return ret

                # SIGINT can't be handled when polling, limit timeout to 1 second.
                msg = self._conn(key).poll(timeout)
                if msg is None:
                    continue
                ret.append(msg.value())
                # LOG.info(msg.value())

            except Exception:
                LOG.error("Kafka DeserializingConsumer for topic: '{key}' running on PID %d died due to exception", os.getpid(), exc_info=True)
                raise    

    def read(self, topic_key, exchange, feed, latest_offset=True):

        # if feed.find(ORDER_INFO) < 0:
        #     return super().read(topic_key, exchange, feed)

        # exclude exchange in topic name
        # key = f"{topic_key}-{feed}".lower()
        key = f'{topic_key}-{feed}-{exchange}'.lower()
        data = self._consume(key, timeout=0.5)
        # if data:
        #     LOG.info("%s: Read %d messages from Kafka", key, len(data))
            
        ret = []

        for message in data:
            if feed in {BALANCES, POSITIONS, ORDER_INFO, FUNDING, TRADES, TICKER}:
                # if exchange is not None:
                #     # LOG.info(f'kafka read in {exchange}')
                #     if message['exchange'] == exchange:
                #         ret.append(message)
                # else:
                ret.append(message)

        return ret

    def delete(self, topic_key, exchange, feed):
        # if feed.find(ORDER_INFO) < 0:
        #     super().delete(topic_key, exchange, feed)
        return

    def reset_latest(self, topic_key, exchange, feed):
        # if feed.find(ORDER_INFO) < 0:
        #     super().reset_latest(topic_key, exchange, feed)
        return
