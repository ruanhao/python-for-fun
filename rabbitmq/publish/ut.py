#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import time
import unittest
import rabbitpy
from rabbitmq_utils import *


URL = 'amqp://guest:guest@localhost:5672/'

class UnitTest(unittest.TestCase):


    def test_publishing_with_unrouted_msg(self):

        with self.subTest("Publishing non-routable messages with mandatory set"):
            '''
            The `mandatory` flag is an argument that's passed along with the Basic.Publish RPC command and
            tells RabbitMQ that if a message isn't routable, it should send the message back to the publisher via a Basic.Return RPC.
            '''
            with rabbitpy.Connection(URL) as connection:
                with self.assertRaises(rabbitpy.exceptions.MessageReturnedException) as assert_raises_context:
                    with connection.channel() as channel:
                        exchange = declare_exchange(channel, 'publishing-with-mandatory-set')
                        body = 'test'
                        message = rabbitpy.Message(channel, body,
                                                   {'content_type': 'text/plain',
                                                    'timestamp': datetime.datetime.now(),
                                                   })
                        # RabbitMQ can't route the message because there's no queue bound to the exchange and routing key.
                        message.publish(exchange, 'no-routing-key', mandatory=True)
                mre = assert_raises_context.exception
                self.assertIn('NO_ROUTE', str(mre))
                self.assertEqual(channel.state_description, 'Closing')

        with self.subTest("Using alternate exchanges for unroutable messages"):
            with rabbitpy.Connection(URL) as connection:
                with connection.channel() as channel:
                    alternate_exchange = declare_exchange(channel, 'alternate-exchange', exchange_type='fanout')
                    exchange = declare_exchange(channel, 'primary-exchange',
                                                exchange_type='topic',
                                                arguments={'alternate-exchange': alternate_exchange.name})
                    dlq = declare_queue(channel, 'unroutable-messages-queue')
                    bind(dlq, alternate_exchange, '#')
                    body = 'test'
                    message = rabbitpy.Message(channel, body, properties('text/plain'))
                    message.publish(exchange, 'no-routing-key', mandatory=True)  # go to dlq
                    message.publish(exchange, 'no-routing-key')  # goto dlq


    def test_publisher_confirms(self):
        with rabbitpy.Connection(URL) as connection:
            with connection.channel() as channel:
                exchange = declare_exchange(channel, 'publisher-comfirms')
                queue = declare_queue(channel, "test-publisher-confirms")
                bind(queue, exchange, "my-routing-key")
                # Prior to publishing any messages, a message publisher must issue a Confirm.Select RPC request to RabbitMQ and
                # wait for a Confirm.SelectOk response to know that delivery confirmations are enabled
                channel.enable_publisher_confirms()
                body = 'test'
                message = rabbitpy.Message(channel, body, properties('text/plain'))
                ack = message.publish(exchange, 'my-routing-key')
                self.assertTrue(ack)
                ack = message.publish(exchange, 'no-routing-key')
                self.assertTrue(ack)  # although no route, still ack
