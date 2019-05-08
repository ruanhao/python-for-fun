#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import datetime
import time
import unittest
import rabbitpy
import random
from rabbitmq_utils import *


URL = 'amqp://guest:guest@localhost:5672/'

class UnitTest(unittest.TestCase):


    def test_handy_publishing_and_consuming(self):
        '''
        Usage of default exchange
        '''
        with rabbitpy.Connection(URL) as connection:
            with connection.channel() as channel:
                queue = declare_queue(channel, '', auto_delete=True)

        routing_key_as_queue_name = queue.name
        # The empty string denotes the default nameless exchange:
        # messages are routed to the queue with the name SPECIFIED BY routing_key, if it exists.
        rabbitpy.publish(URL, '', routing_key_as_queue_name, 'hello world')

        for message in rabbitpy.consume(URL, queue.name):
            message.pprint()
            message.ack()
            break

    def test_ack_mode(self):
        channel = get_channel(URL)
        exchange = declare_exchange(channel, 'test-ack-mode-exchange')
        queue = declare_queue(channel, "test-ack-mode-queue")
        origin_len = len(queue)
        bind(queue, exchange, "my-routing-key")
        random_num = random.randint(1, 5)
        print(f'random number of msgs: {random_num}, origin_len: {origin_len}')
        for i in range(0, random_num):
            message = rabbitpy.Message(channel, f'test ack maeesge-{i}', properties())
            message.publish(exchange, 'my-routing-key')
        time.sleep(1)
        self.assertEqual(len(queue), random_num + origin_len)
        consumer = queue.consume(no_ack=False)
        time.sleep(1)
        next(consumer)          # start generator (read all messages)
        self.assertEqual(len(queue), 0)
        self.assertEqual(get_unacked_number(queue.name), random_num + origin_len)

    def test_no_ack_mode(self):
        channel = get_channel(URL)
        exchange = declare_exchange(channel, 'test-no-ack-mode-exchange')
        queue = declare_queue(channel, "test-no-ack-mode-queue")
        origin_len = len(queue)
        bind(queue, exchange, "my-routing-key")
        random_num = random.randint(1, 5)
        print(f'random number of msgs: {random_num}, origin_len: {origin_len}')
        for i in range(0, random_num):
            message = rabbitpy.Message(channel, f'test no-ack maeesge-{i}', properties())
            message.publish(exchange, 'my-routing-key')
        time.sleep(1)
        self.assertEqual(len(queue), random_num + origin_len)
        consumer = queue.consume(no_ack=True)
        time.sleep(1)
        next(consumer)          # start generator (read all messages)
        self.assertEqual(len(queue), 0)
        self.assertEqual(get_unacked_number(queue.name), 0)


    def test_multi_consumers(self):
        channel = get_channel(URL)
        exchange = declare_exchange(channel, 'test-multi-consumers-exchange')
        queue = declare_queue(channel, "test-multi-consumers-queue")
        bind(queue, exchange, "my-routing-key")
        total = 0
        origin_len = len(queue)
        random_num = random.randint(1, 10)
        def worker1():
            nonlocal total
            consumer = queue.consume()
            for msg in consumer:
                print(f"Get msg in worker1 (consumer tag: {queue.consumer_tag})")
                total += 1
                msg.ack()
        def worker2():
            nonlocal total
            q = declare_queue(channel, queue.name)
            consumer = q.consume()
            for msg in consumer:
                print(f"Get msg in worker2 (consumer tag: {q.consumer_tag})")
                total += 1
                msg.ack()
        t1 = threading.Thread(target=worker1, name='Worker1')
        t2 = threading.Thread(target=worker2, name='Worker2')
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        for i in range(0, random_num):
            message = rabbitpy.Message(channel, f'test maeesge-{i}', properties())
            message.publish(exchange, 'my-routing-key')
        time.sleep(1)
        self.assertEqual(total, random_num + origin_len)


    def test_prefetching_via_qos_settings(self):
        channel = get_channel(URL)
        random_prefetch_count = random.randint(1, 10)
        print(f"prefetch count: {random_prefetch_count}")
        channel.prefetch_count(random_prefetch_count)
        exchange = declare_exchange(channel, 'test-prefetching-via-qos-exchange')
        queue = declare_queue(channel, "test-prefetching-via-qos-queue")
        bind(queue, exchange, "my-routing-key")
        for i in range(0, random_prefetch_count * 2):
            message = rabbitpy.Message(channel, f'test maeesge-{i}', properties())
            message.publish(exchange, 'my-routing-key')
        consumer = queue.consume()  # can also use queue.consume(prefetch=random_prefetch_count)
        next(consumer)          # start consuming
        time.sleep(1)
        self.assertEqual(get_unacked_number(queue.name), random_prefetch_count)


    def test_acknowledging_multiple_messages_at_once(self):
        channel = get_channel(URL)
        exchange = declare_exchange(channel, 'test-ack-multi-msgs-exchange')
        queue = declare_queue(channel, "test-ack-multi-msgs-queue")
        bind(queue, exchange, "my-routing-key")
        origin_len = len(queue)
        random_count = random.randint(2, 10)
        for i in range(0, random_count):
            message = rabbitpy.Message(channel, f'test maeesge-{i}', properties())
            message.publish(exchange, 'my-routing-key')
        consumer = queue.consume()
        for _ in range(0, random_count - 1):
            msg = next(consumer)
        msg.ack(all_previous=True)
        self.assertEqual(get_unacked_number(queue.name), 1 + origin_len)
