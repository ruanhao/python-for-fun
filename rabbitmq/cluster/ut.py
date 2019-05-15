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


DOCKER_NETWORK = 'rabbitmq-cluster'
BASIC_DOCKER_OPTS = f'--rm -d --network {DOCKER_NETWORK} -e RABBITMQ_ERLANG_COOKIE=mycookie -e RABBITMQ_NODENAME=rabbit'
NODE_NUMBER = 3
RABBIT_1_PORT = 5672
RABBIT_2_PORT = 5673
RABBIT_3_PORT = 5674
RABBIT_1_MANAGEMENT_PORT = RABBIT_1_PORT + 10000
RABBIT_2_MANAGEMENT_PORT = RABBIT_2_PORT + 10000
RABBIT_3_MANAGEMENT_PORT = RABBIT_3_PORT + 10000


class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")

    def _test_basic_functions(self, port=5672):
        channel = pika_channel(port=port)
        exchange = pika_exchange_declare(channel, f'{get_uuid()}-exchange', exchange_type='topic')
        queue = pika_queue_declare(channel, f'{get_uuid()}-queue')
        pika_queue_bind(channel, queue, exchange, 'a.b.c')
        pika_simple_publish(channel, exchange, 'a.b.c', 'hello world')
        self.assertEqual(pika_basic_get(channel, queue), 'hello world')


    def _test_adding_new_node(self, i, target_node='rabbit@rabbit1', node_type='ram'):
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit{i} --name rabbit{i} -p {15672+i-1}:15672 -p {5672+i-1}:5672 rabbitmq:3-management')
        run(f'docker exec rabbit{i} rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')

        run(f'docker exec rabbit{i} rabbitmqctl stop_app')
        run(f'docker exec rabbit{i} rabbitmqctl reset')  # empty metadata so it can be joined and acquire the metadata of the cluster
        run(f'docker exec rabbit{i} rabbitmqctl join_cluster --{node_type} {target_node}')
        run(f'docker exec rabbit{i} rabbitmqctl start_app')



    def test_creating_cluster(self):
        '''
        rabbit1 (disc)
        rabbit2 (disc)
        rabbit3 (ram)
        '''
        run('docker stop `docker ps --format="{{.Names}}" | grep rabbit`', True)
        run(f'docker network rm {DOCKER_NETWORK}', True)
        run(f'docker network create {DOCKER_NETWORK}')
        for i in range(1, NODE_NUMBER+1):
            run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit{i} --name rabbit{i} -p {15672+i-1}:15672 -p {5672+i-1}:5672 rabbitmq:3-management')
            run(f'docker exec rabbit{i} rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')

        # setup rabbit2
        run('docker exec rabbit2 rabbitmqctl stop_app')
        run('docker exec rabbit2 rabbitmqctl reset')  # empty metadata so it can be joined and acquire the metadata of the cluster
        run('docker exec rabbit2 rabbitmqctl join_cluster --disc rabbit@rabbit1')
        run('docker exec rabbit2 rabbitmqctl start_app')

        # setup rabbit3
        run('docker exec rabbit3 rabbitmqctl stop_app')
        run('docker exec rabbit3 rabbitmqctl reset')
        run('docker exec rabbit3 rabbitmqctl join_cluster --ram rabbit@rabbit1')
        run('docker exec rabbit3 rabbitmqctl start_app')

        run(f'docker exec rabbit1 rabbitmqctl await_online_nodes {NODE_NUMBER}')
        run('docker exec rabbit1 rabbitmqctl cluster_status')


    def test_pulling_out_disc_node_from_cluster(self):
        with self.subTest("Pulling out one disc node normally"):
            self.test_creating_cluster()
            run(f'docker exec rabbit2 rabbitmqctl stop_app')
            # When the node being reset is a part of a cluster,
            # the command also communicates with the disk nodes in the cluster to tell them that the node is leaving.
            run(f'docker exec rabbit2 rabbitmqctl reset')
            self.assertEquals(len(get_running_nodes()), 2)
            self._test_basic_functions()
            self._test_adding_new_node(i=4)
            run(f'docker exec rabbit1 rabbitmqctl await_online_nodes 3')
            self.assertIn('rabbit@rabbit4', get_running_nodes())


        with self.subTest("Pulling out one disc node abruptly"):
            self.test_creating_cluster()
            run('docker stop rabbit2')
            run('docker exec rabbit1 rabbitmqctl cluster_status')
            self._test_basic_functions() # ok
            self._test_adding_new_node(i=4) # ok
            run(f'docker exec rabbit1 rabbitmqctl await_online_nodes 3')
            self.assertIn('rabbit@rabbit4', get_running_nodes())
            run('docker exec rabbit1 rabbitmqctl cluster_status')

        with self.subTest("Pulling out all disc nodes normally"):
            '''
            Pull out rabbit1 and rabbit2
            rabbit3 untouched
            '''
            self.test_creating_cluster()
            channel_at_rabbit2 = pika_channel(port=RABBIT_2_PORT)
            channel_at_rabbit3 = pika_channel(port=RABBIT_3_PORT)
            queue_at_rabbit2 = pika_queue_declare(channel_at_rabbit2, '')
            queue_at_rabbit3 = pika_queue_declare(channel_at_rabbit3, '')
            pika_simple_publish(channel_at_rabbit2, '', queue_at_rabbit2, 'hello')

            self.assertEqual(pika_basic_get(channel_at_rabbit3, queue_at_rabbit2), 'hello')
            pika_simple_publish(channel_at_rabbit2, '', queue_at_rabbit3, "message sent before")


            run('docker exec rabbit1 rabbitmqctl stop_app')
            run('docker exec rabbit1 rabbitmqctl reset')  # reset disc node rabbit@rabbit1
            run('docker exec rabbit2 rabbitmqctl stop_app')
            self.assertEqual(get_running_nodes_types(RABBIT_3_MANAGEMENT_PORT), (0, 1))

            another_channel_at_rabbit3 = pika_channel(port=RABBIT_3_PORT)  # still can connect to cluster
            # can retrieve msg sent before
            self.assertEqual(pika_basic_get(another_channel_at_rabbit3, queue_at_rabbit3), 'message sent before')
            with self.assertRaises(pika.exceptions.ChannelClosedByBroker) as raised_exception:
                pika_basic_get(another_channel_at_rabbit3, queue_at_rabbit2)
            self.assertIn(f"no queue '{queue_at_rabbit2}'", raised_exception.exception.reply_text)  # queue not available
            self.assertEqual(raised_exception.exception.reply_code, 404)


            self._test_basic_functions(port=RABBIT_3_PORT)
            self._test_adding_new_node(i=4, target_node='rabbit@rabbit3')  # ok to add ram node
            self.assertEqual(get_running_nodes_types(RABBIT_3_MANAGEMENT_PORT), (0, 2))

            with self.assertRaises(Exception) as raised_exception:
                self._test_adding_new_node(i=5, target_node='rabbit@rabbit2')
            self.assertIn('mnesia_not_running', raised_exception.exception.err_msg)

            with self.assertRaises(Exception) as raised_exception:
                run('docker exec rabbit2 rabbitmqctl reset')  # reset disc node rabbit@rabbit2
            self.assertEqual(raised_exception.exception.err_code, 69)
            self.assertIn('cannot reset a node when it is the only disc node in a cluster', raised_exception.exception.err_msg)

            self._test_adding_new_node(i=6, target_node='rabbit@rabbit3', node_type='disc') # ok to add disc node
            self.assertEqual(get_running_nodes_types(RABBIT_3_MANAGEMENT_PORT), (1, 2))


        with self.subTest("Pulling out all disc nodes abruptly"):
            '''
            Pull out rabbit1 and rabbit2
            rabbit3 untouched
            '''
            self.test_creating_cluster()
            channel_at_rabbit2 = pika_channel(port=RABBIT_2_PORT)
            channel_at_rabbit3 = pika_channel(port=RABBIT_3_PORT)
            queue_at_rabbit2 = pika_queue_declare(channel_at_rabbit2, '')
            queue_at_rabbit3 = pika_queue_declare(channel_at_rabbit3, '')
            pika_simple_publish(channel_at_rabbit2, '', queue_at_rabbit2, 'hello')
            self.assertEqual(pika_basic_get(channel_at_rabbit3, queue_at_rabbit2), 'hello')
            pika_simple_publish(channel_at_rabbit2, '', queue_at_rabbit3, "message sent before")

            run('docker stop rabbit1')
            self._test_basic_functions(port=RABBIT_3_PORT)
            self._test_adding_new_node(i=4, target_node='rabbit@rabbit3')  # ok to add ram node
            self.assertEqual(get_running_nodes_types(RABBIT_3_MANAGEMENT_PORT), (1, 2))

            run('docker stop rabbit2')
            self._test_basic_functions(port=RABBIT_3_PORT)
            self._test_adding_new_node(i=5, target_node='rabbit@rabbit3')  # ok to add ram node
            self._test_adding_new_node(i=6, target_node='rabbit@rabbit3', node_type='disc')  # ok to add ram node
            self.assertEqual(get_running_nodes_types(RABBIT_3_MANAGEMENT_PORT), (1, 3))

            another_channel_at_rabbit3 = pika_channel(port=RABBIT_3_PORT)  # still can connect to cluster
            self.assertEqual(pika_basic_get(another_channel_at_rabbit3, queue_at_rabbit3), 'message sent before')
