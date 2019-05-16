#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
import threading
import datetime
import time
import unittest
import rabbitpy
import random
import os
from subprocess import TimeoutExpired
from contextlib import redirect_stderr, redirect_stdout
from rabbitmq_utils import *


DOCKER_NETWORK = 'rabbitmq-cluster'
BASIC_DOCKER_OPTS = f'--rm -d --cap-add=NET_ADMIN --cap-add=NET_RAW --network {DOCKER_NETWORK} -e RABBITMQ_ERLANG_COOKIE=mycookie -e RABBITMQ_NODENAME=rabbit'
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

    def _test_creating_cluster(self):
        print("Creating cluster ...")
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_creating_cluster()


    def test_reset(self):
        self.test_creating_cluster()
        run('docker stop rabbit1 rabbit2')
        run('docker exec rabbit3 rabbitmqctl stop_app')
        _, stderr = run('docker exec rabbit3 rabbitmqctl reset', True)
        self.assertIn('cannot_create_standalone_ram_node', stderr)
        run('docker exec rabbit3 rabbitmqctl force_reset')

        self.test_creating_cluster()
        run('docker stop rabbit2 rabbit3')
        run('docker exec rabbit1 rabbitmqctl stop_app')
        _, stderr = run('docker exec rabbit1 rabbitmqctl reset', True)
        self.assertIn('You cannot leave a cluster if no online nodes are present', stderr)
        run('docker exec rabbit1 rabbitmqctl force_reset')


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

    def test_rejoining(self):
        # with self.subTest("Restarting ram node first"):
        #     self._test_creating_cluster()
        #     self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
        #     for i in range(1, 4):
        #         run(f"docker exec rabbit{i} rabbitmqctl stop_app")
        #     with self.assertRaises(Exception):
        #         run("docker exec rabbit3 rabbitmqctl start_app")  # Mnesia could not connect to any disc nodes

        # with self.subTest("Restarting node (not last stopped disc)"):
        #     self._test_creating_cluster()
        #     self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
        #     for i in range(1, 4):
        #         run(f"docker exec rabbit{i} rabbitmqctl stop_app")

        #     with self.assertRaises(TimeoutExpired):
        #         # restart disc node that is not stopped last
        #         run("docker exec rabbit1 rabbitmqctl start_app", timeout=30)  # Waiting for Mnesia tables


        #     run("docker exec rabbit2 rabbitmqctl start_app")
        #     run("docker exec rabbit3 rabbitmqctl start_app")
        #     self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram






        # with self.subTest("Restarting node (last stopped disc)"):
        #     self._test_creating_cluster()
        #     self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
        #     for i in range(1, 4):
        #         run(f"docker exec rabbit{i} rabbitmqctl stop_app")

        #     # restart node that is stopped last as disc
        #     run("docker exec rabbit2 rabbitmqctl start_app")
        #     # the restarting sequence of rabbit1 and rabbit3 does not matter
        #     run("docker exec rabbit1 rabbitmqctl start_app")
        #     run("docker exec rabbit3 rabbitmqctl start_app")
        #     self.assertEqual(get_running_nodes_types(), (2, 1))

        with self.subTest("Restarting disc node first (first stopped)"):
            self._test_creating_cluster()
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
            for i in range(1, 4):
                run(f"docker exec rabbit{i} rabbitmqctl stop_app")


            '''
            通常情况下，当关闭整个 RabbitMQ 集群时，重启的第一个节点应该是最后关闭的节点，因为它可以看到其他节点所看不到的事情。
            但是有时会有一些异常情况出现，比如整个集群都掉电而所有节点都认为它不是最后一个关闭的。
            在这种情况下，可以调用 rabbitmqctl force_boot 命令，这就告诉节点*下次*可以无条件地启动节点。

            如果最后一个关闭的节点永久丢失了，可以优先使用 rabbitmqctl forget_cluster_node 命令，因为它可以确保镜像队列的正常运转。
            使用 forget_cluster_node 命令的话，需要删除的节点必须是 offline ，执行命令的节点必须 online ，（否则需要指定 --offline 参数）。
            注意：如果指定执行命令的节点为 --offline ，意味着不能存在 Erlang node ，因为 rabbitmqctl 需要 mock 一个同名的 node 。
            '''
            run("docker exec rabbit1 rabbitmqctl force_boot")  # Ensures that the node will start NEXT TIME, even if it was not the last to shut down.
            run("docker exec rabbit1 rabbitmqctl start_app")
            run("docker exec rabbit2 rabbitmqctl start_app")
            run("docker exec rabbit3 rabbitmqctl start_app")
            self.assertEqual(get_running_nodes_types(), (2, 1))











    def test_update_cluster_nodes(self):
        '''
        在集群中的节点应用启动前先咨询 clusternode 节点的最新信息，井更新相应的集群信息。 这个和 join_cluster 不同，它不加入集群。
        考虑这样一种情况，节点 A 和节点 B 在集群中，当节点 A 离线，节点 C 又和节点 B 组成了一个集群，然后节点 B 又离开了集群，
        当 A 醒来的时候，它会尝试联系节点 B，但是这样会失败， 因为节点 B 己经不在集群中了。
        Rabbitmqctl update_cluster_nodes C 可以解决这种场景下出现的问题。
        '''
        run('docker stop `docker ps --format="{{.Names}}" | grep rabbit`', True)
        run(f'docker network rm {DOCKER_NETWORK}', True)
        run(f'docker network create {DOCKER_NETWORK}')

        # rabbit_a
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_a --name rabbit_a -p 15672:15672 -p 5672:5672 rabbitmq:3-management')
        run('docker exec rabbit_a rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')

        # rabbit_b
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_b --name rabbit_b -p 15673:15672 -p 5673:5672 rabbitmq:3-management')
        run('docker exec rabbit_b rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')
        run('docker exec rabbit_b rabbitmqctl stop_app')
        run('docker exec rabbit_b rabbitmqctl reset')
        run('docker exec rabbit_b rabbitmqctl join_cluster --ram rabbit@rabbit_a')
        run('docker exec rabbit_b rabbitmqctl start_app')
        self.assertEqual(get_running_nodes_types(), (1, 1))

        run('docker exec rabbit_a rabbitmqctl stop_app')  # rabbit_a offline

        # rabbit_c
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_c --name rabbit_c -p 15674:15672 -p 5674:5672 rabbitmq:3-management')
        run('docker exec rabbit_c rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')
        run('docker exec rabbit_c rabbitmqctl stop_app')
        run('docker exec rabbit_c rabbitmqctl reset')
        run('docker exec rabbit_c rabbitmqctl join_cluster --ram rabbit@rabbit_b')
        run('docker exec rabbit_c rabbitmqctl start_app')
        self.assertEqual(get_running_nodes_types(15673), (0, 2))

        # rabbit_b walks away
        run('docker exec rabbit_b rabbitmqctl stop_app')
        run('docker exec rabbit_b rabbitmqctl reset')

        # rabbit_a wakes up
        run('docker exec rabbit_a rabbitmqctl start_app')
        all_nodes = get_nodes()
        rabbit_a = key_find(all_nodes, 'name', 'rabbit@rabbit_a')
        self.assertTrue(rabbit_a['running'])
        rabbit_b = key_find(all_nodes, 'name', 'rabbit@rabbit_b')
        self.assertFalse(rabbit_b['running'])  # rabbit_b still there but not running
        run('docker exec rabbit_a rabbitmqctl cluster_status')

        run('docker exec rabbit_a rabbitmqctl stop_app')
        run('docker exec rabbit_a rabbitmqctl update_cluster_nodes rabbit@rabbit_c')  # query cluster info from rabbit_c
        run('docker exec rabbit_a rabbitmqctl start_app')
        all_nodes = get_nodes()
        rabbit_a = key_find(all_nodes, 'name', 'rabbit@rabbit_a')
        self.assertTrue(rabbit_a['running'])
        rabbit_b = key_find(all_nodes, 'name', 'rabbit@rabbit_b')
        self.assertIsNone(rabbit_b)  # no rabbit_b
        rabbit_c = key_find(all_nodes, 'name', 'rabbit@rabbit_c')
        self.assertTrue(rabbit_c['running'])
        run('docker exec rabbit_a rabbitmqctl cluster_status')


    def test_sync_queue(self):
        '''
        rabbitmqctl sync_queue
        指示未同步队列 queue 的 slave 镜像可以同步 master 镜像的内容。
        同步期间此队列会被阻塞(所有此队列的生产消费者都会被阻塞)，直到同步完成。
        此条命令执行成功的前提是队列 queue 配置了镜像。
        注意，未同步队列中的消息被耗尽后，最终也会变成同步，此命令主要用于未耗尽的队列。

        可以使用 rabbitmqctl cancel_sync_queue 取消队列镜像同步的操作。
        '''
        pass
