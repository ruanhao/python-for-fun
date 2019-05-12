#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
import threading
import datetime
import time
import unittest
import rabbitpy
import random
from rabbitmq_utils import *




class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")


    def test_direct_exchange(self):
        '''
        test-direct-exchange -- test,dev --> test-direct-exchange-queue1
                            `----- qa -----> test-direct-exchange-queue2
                            `---- test ----> test-direct-exchange-queue3
        '''
        channel = pika_channel()
        exchange = pika_exchange_declare(channel, "test-direct-exchange", exchange_type='direct')
        queue1 = pika_queue_declare(channel, "test-direct-exchange-queue1")
        queue2 = pika_queue_declare(channel, "test-direct-exchange-queue2")
        queue3 = pika_queue_declare(channel, "test-direct-exchange-queue3")

        pika_queue_bind(channel, queue1, exchange, 'test')
        pika_queue_bind(channel, queue1, exchange, 'dev')  # Queue 1 is bound to the exchange with both "test" and "dev"
        pika_queue_bind(channel, queue2, exchange, 'qa')
        pika_queue_bind(channel, queue3, exchange, 'test')

        pika_simple_publish(channel, exchange, 'test', "shanghai")
        pika_simple_publish(channel, exchange, 'dev', "beijing")
        pika_simple_publish(channel, exchange, 'qa', "guangzhou")


        self.assertEqual(pika_basic_get(channel, queue1), 'shanghai')
        self.assertEqual(pika_basic_get(channel, queue1), 'beijing')
        self.assertEqual(pika_basic_get(channel, queue2), 'guangzhou')
        self.assertEqual(pika_basic_get(channel, queue3), 'shanghai')


    def test_fanout_exchange(self):
        channel = pika_channel()
        exchange = pika_exchange_declare(channel, "test-fanout-exchange", exchange_type='fanout')
        queue1 = pika_queue_declare(channel, "test-fanout-exchange-queue1")
        queue2 = pika_queue_declare(channel, "test-fanout-exchange-queue2")

        pika_queue_bind(channel, queue1, exchange)
        pika_queue_bind(channel, queue2, exchange)

        now = str(datetime.datetime.now())
        pika_simple_publish(channel, exchange, '', now)
        self.assertEqual(pika_basic_get(channel, queue1), now)
        self.assertEqual(pika_basic_get(channel, queue2), now)


    def test_topic_exchange(self):
        '''
        exchange -- info.#     --> queue1
                `-- #.software --> queue2
                `-- *.dev.*    --> queue3
        '''
        channel = pika_channel()
        exchange = pika_exchange_declare(channel, "test-topic-exchange", exchange_type='topic')
        queue1 = pika_queue_declare(channel, "test-topic-exchange-queue1")
        queue2 = pika_queue_declare(channel, "test-topic-exchange-queue2")
        queue3 = pika_queue_declare(channel, "test-topic-exchange-queue3")

        pika_queue_bind(channel, queue1, exchange, 'info.#')
        pika_queue_bind(channel, queue2, exchange, '#.software')
        pika_queue_bind(channel, queue3, exchange, '*.dev.*')

        pika_simple_publish(channel, exchange, 'info.test.hardware', "shanghai")
        self.assertEqual(pika_queue_counters(channel, queue2)[1], 0)
        self.assertEqual(pika_queue_counters(channel, queue3)[1], 0)
        self.assertEqual(pika_basic_get(channel, queue1), 'shanghai')

        pika_simple_publish(channel, exchange, 'info.dev.software', "beijing")
        self.assertEqual(pika_basic_get(channel, queue1), 'beijing')
        self.assertEqual(pika_basic_get(channel, queue2), 'beijing')
        self.assertEqual(pika_basic_get(channel, queue3), 'beijing')

        pika_simple_publish(channel, exchange, 'alert.dev.hardware', "guangzhou")
        self.assertEqual(pika_queue_counters(channel, queue1)[1], 0)
        self.assertEqual(pika_queue_counters(channel, queue2)[1], 0)
        self.assertEqual(pika_basic_get(channel, queue3), 'guangzhou')

    def test_headers_exchange(self):
        '''
        Using the headers table in the message properties.

        exchange -- {'x-match': 'all', 'env': 'dev', 'severity': 'info'} --> all_match_queue
                `-- {'x-match': 'any', 'env': 'dev', 'severity': 'normal'} --> any_match_queue
        '''
        channel = pika_channel()
        exchange = pika_exchange_declare(channel, "test-header-exchange", exchange_type='headers')
        all_match_queue = pika_queue_declare(channel, "test-header-exchange-all-match-queue")
        any_match_queue = pika_queue_declare(channel, "test-header-exchange-any-match-queue")

        # If x-match is 'any', messages will be routed if any of the headers table values match any of the binding values.
        # If x-match is 'all', all values passed in as Queue.Bind arguments must be matched.

        pika_queue_bind(channel,
                        all_match_queue,
                        exchange,
                        arguments={
                            'x-match': 'all',
                            'env': 'dev',
                            'severity': 'info',
                        }
        )
        pika_queue_bind(channel,
                        any_match_queue,
                        exchange,
                        arguments={
                            'x-match': 'any',
                            'env': 'dev',
                            'severity': 'normal',
                        })
        channel.basic_publish(exchange, '', 'shanghai', pika.BasicProperties(
            headers={
                'env': 'dev',
            },
        ))
        channel.basic_publish(exchange, '', 'beijing', pika.BasicProperties(
            headers={
                'env': 'dev',
                'severity': 'info'
            },
        ))
        self.assertEqual(pika_queue_counters(channel, all_match_queue)[1], 1)
        self.assertEqual(pika_queue_counters(channel, any_match_queue)[1], 2)
        self.assertEqual(pika_basic_get(channel, all_match_queue), 'beijing')
        self.assertEqual(pika_basic_get(channel, any_match_queue), 'shanghai')
        self.assertEqual(pika_basic_get(channel, any_match_queue), 'beijing')

    def test_exchange_to_exchange_routing(self):
        '''
        exchange1 --a.b.#--> exchange2 --a.b.c--> queue2
           \
            `--a.c.#--> queue1
        '''
        channel = pika_channel()
        exchange1 = pika_exchange_declare(channel, "test-x2x-routing-exchange1", exchange_type='topic')
        exchange2 = pika_exchange_declare(channel, "test-x2x-routing-exchange2", exchange_type='topic')
        queue1 = pika_queue_declare(channel, 'test-x2x-routing-queue1')
        queue2 = pika_queue_declare(channel, 'test-x2x-routing-queue2')

        pika_exchange_bind(channel, exchange2, exchange1, 'a.b.#')
        pika_queue_bind(channel, queue2, exchange2, 'a.b.c')
        pika_queue_bind(channel, queue1, exchange1, 'a.c.#')

        pika_simple_publish(channel, exchange1, 'a.b.c', 'shanghai')
        self.assertEqual(pika_queue_counters(channel, queue1)[1], 0)
        self.assertEqual(pika_queue_counters(channel, queue2)[1], 1)
        self.assertEqual(pika_basic_get(channel, queue2), 'shanghai')

        pika_simple_publish(channel, exchange1, 'a.c.b', 'beijing')
        self.assertEqual(pika_queue_counters(channel, queue1)[1], 1)
        self.assertEqual(pika_queue_counters(channel, queue2)[1], 0)
        self.assertEqual(pika_basic_get(channel, queue1), 'beijing')


    def test_consistent_hashing_exchange(self):
        '''
        The hashing distributes ROUTING KEYS among queues, NOT message payloads among queues;
        all messages with the same routing key will go the same queue.

        So, if you wish for queue A to receive twice as many routing keys routed to it than are routed to queue B,
        then you bind the queue A with a binding key of TWICE THE NUMBER (as a string -- binding keys are always strings)
        of the binding key of the binding to queue B.

        Note this is only the case IF YOUR ROUTING KEYS ARE EVENLY DISTRIBUTED IN THE HASH SPACE.
        If, for example, only two distinct routing keys are used on all the messages,
        there's a chance both keys will route (consistently!) to the same queue,
        even though other queues have higher values in their binding key.
        With a larger set of routing keys used, the statistical distribution of routing keys approaches the ratios of the binding keys.


        exchange --10--> consistent-hash-queue1
               `---10--> consistent-hash-queue2
               `---30--> consistent-hash-queue3
        '''
        run("docker exec -it rabbit rabbitmq-plugins enable rabbitmq_consistent_hash_exchange", True)
        channel = pika_channel()
        exchange = pika_exchange_declare(channel, "test-consitent-hashing-exchange", exchange_type='x-consistent-hash')
        queues = [f'consistent-hash-queue{i}' for i in range(1, 4)]
        for i, q in enumerate(queues, 1):
            pika_queue_declare(channel, q)
            if i == 2:
                weight = '10'
            else:
                weight = str(i*10)
            pika_queue_bind(channel, q, exchange, routing_key=weight)

        with self.subTest("DETERMINISTICALLY route messages based on hash value of routing key"):
            pika_queue_purge(channel, queues)
            rk = 'helloworkd'
            for _ in range(0, 1000):
                pika_simple_publish(channel, exchange, rk, 'test msg')
            msg_counter_for_queues = [pika_queue_counters(channel, q)[1] for q in queues]
            self.assertEqual(msg_counter_for_queues.count(0), len(queues) - 1)


        with self.subTest("Evenly distributed"):
            pika_queue_purge(channel, queues)
            for i in range(0, 1000):
                rk = f'rk{i}'
                pika_simple_publish(channel, exchange, rk, 'test msg')
            msg_counter_for_queues = [pika_queue_counters(channel, q)[1] for q in queues]
            counter1, counter2, counter3 = msg_counter_for_queues
            self.assertAlmostEqual(counter1/counter2, 1, places=0)
            self.assertAlmostEqual(counter3/counter1, 3, places=0)
            self.assertAlmostEqual(counter3/counter2, 3, places=0)


        with self.subTest("Routing on header"):
            '''
            Under most circumstances the routing key is a good choice for something to hash.
            However, in some cases it is necessary to use the routing key for some other purpose,
            for example with more complex routing involving exchange to exchange bindings
            (first exchange if of type headers while the second of type x-consistent-hash).

            my-headers-exchange --{'env': 'dev'}--> consistent-hashing-header-exchange --10--> consistent-hash-header-queue1
                                                                                       `-20--> consistent-hash-header-queue2

            '''
            queues = [f'consistent-hash-header-queue{i}' for i in range(1, 3)]
            my_headers_exchange = pika_exchange_declare(channel, "my-headers-exchange", exchange_type='headers')
            consistent_hashing_header_exchange = pika_exchange_declare(channel,
                                                                       "consistent-hashing-header-exchange",
                                                                       exchange_type='x-consistent-hash',
                                                                       arguments={'hash-header': 'hash-on'}
            )
            pika_exchange_bind(channel,
                               consistent_hashing_header_exchange,
                               my_headers_exchange,
                               arguments={
                                   'x-match': 'all',
                                   'env': 'dev',
                               }
            )
            for i, q in enumerate(queues, 1):
                pika_queue_declare(channel, q)
                pika_queue_bind(channel, q, consistent_hashing_header_exchange, routing_key=str(i*10))

            for i in range(0, 1000):
                rk = f'rk{i}'
                channel.basic_publish(my_headers_exchange, '', 'test msg', pika.BasicProperties(
                    headers={
                        'env': 'dev',
                        'hash-on': rk,
                    },
                ))

            counter1, counter2 = [pika_queue_counters(channel, q)[1] for q in queues]
            self.assertAlmostEqual(counter2/counter1, 2, places=0)



if __name__ == '__main__':
    unittest.main(verbosity=2)