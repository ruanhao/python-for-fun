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
from troposphere import Output, Template, Ref, GetAtt
from aws_utils import *
from rabbitmq_utils import *

SSH_OPTIONS = "-o StrictHostKeyChecking=no -o LogLevel=ERROR"
QUEUE_INFOS = 'name pid slave_pids synchronised_slave_pids'
RABBITMQ_VERSION = "3.7.14"
DOCKER_NETWORK = 'rabbitmq-cluster'
BASIC_DOCKER_OPTS = f'--rm -d --cap-add=NET_ADMIN --cap-add=NET_RAW --network {DOCKER_NETWORK} -e RABBITMQ_ERLANG_COOKIE=mycookie -e RABBITMQ_NODENAME=rabbit'
NODE_NUMBER = 3
RABBIT_1_PORT = 5672
RABBIT_2_PORT = 5673
RABBIT_3_PORT = 5674
RABBIT_1_MANAGEMENT_PORT = RABBIT_1_PORT + 10000
RABBIT_2_MANAGEMENT_PORT = RABBIT_2_PORT + 10000
RABBIT_3_MANAGEMENT_PORT = RABBIT_3_PORT + 10000

IMAGE_ID = 'ami-091b408e76a06ce1c'  # this image is located in Ohio

class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="subprocess.*")


    def _test_basic_functions(self, port=5672):
        channel = pika_channel(port=port)
        exchange = pika_exchange_declare(channel, f'{get_uuid()}-exchange', exchange_type='topic')
        queue = pika_queue_declare(channel, f'{get_uuid()}-queue')
        pika_queue_bind(channel, queue, exchange, 'a.b.c')
        pika_simple_publish(channel, exchange, 'a.b.c', 'hello world')
        self.assertEqual(pika_basic_get(channel, queue), 'hello world')

    def _wait_until(self, func, expect, desc=None, delay=3, tries=10):
        while tries >= 0:
            actual = func()
            if actual == expect:
                return
            time.sleep(delay)
            tries -= 1
        self.fail(f"actual[{actual}] != expected[{expected}] ({desc})")


    def _test_adding_new_node(self, i, target_node='rabbit@rabbit1', node_type='ram'):
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit{i} --name rabbit{i} -p {15672+i-1}:15672 -p {5672+i-1}:5672 rabbitmq:{RABBITMQ_VERSION}-management')
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
            run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit{i} --name rabbit{i} -p {15672+i-1}:15672 -p {5672+i-1}:5672 rabbitmq:{RABBITMQ_VERSION}-management')
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

    def test_creating_cluster_on_aws(self, instance_num=3, additional_disc_index_list=None):
        if additional_disc_index_list is None:
            additional_disc_index_list = []
        image_id = IMAGE_ID
        test_stack_name = 'TestRabbitMQ'
        init_cf_env(test_stack_name)
        ###
        t = Template()
        sg = ts_add_security_group(t)
        for i in range(1, instance_num+1):
            ts_add_instance_with_public_ip(t, Ref(sg), name=f"RabbitMQ{i}", image_id=image_id, tag='rabbitmq')

        t.add_output([Output(f'PublicIP{i}', Value=GetAtt(f"RabbitMQ{i}", "PublicIp")) for i in range(1, instance_num+1)])
        dump_template(t, True)
        cf_client.create_stack(
            StackName=test_stack_name,
            TemplateBody=t.to_yaml(),
        )
        cf_client.get_waiter('stack_create_complete').wait(StackName=test_stack_name)
        outputs = cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs']
        time.sleep(10)           # wait for ssh servce starting up
        ips = {}
        snames = {}
        for i in range(1, instance_num+1):
            k = f'rabbit{i}'
            public_ip = key_find(outputs, 'OutputKey', f'PublicIP{i}')['OutputValue']
            snames[k] = run(f"ssh {SSH_OPTIONS} ec2-user@{public_ip} hostname -s", True)[0]
            ips[k] = public_ip

        print(f"Cluster established.\n{ips}\n{snames}")

        for i in range(2, instance_num+1):
            k = f'rabbit{i}'
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips[k]} sudo rabbitmqctl stop_app")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips[k]} sudo rabbitmqctl reset")
            disc_type = 'disc' if i in additional_disc_index_list else 'ram'
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips[k]} sudo rabbitmqctl join_cluster --{disc_type} rabbit@{snames['rabbit1']}")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips[k]} sudo rabbitmqctl start_app")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl await_online_nodes {instance_num}")
        return (ips, snames)


    def _test_creating_cluster(self):
        print("Creating cluster with Docker...")
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_creating_cluster()

    def _test_creating_cluster_on_aws(self, instance_num=3, additional_disc_index_list=None):
        if additional_disc_index_list is None:
            additional_disc_index_list = []
        print(f"Creating cluster on AWS... (instance_num: {instance_num}, additional_disc_index_list: {additional_disc_index_list})")
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                ips, snames = self.test_creating_cluster_on_aws(instance_num, additional_disc_index_list)
        print(f"Cluster established.\n{ips}\n{snames}")
        return (ips, snames)



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

    def test_rejoining_order(self):
        with self.subTest("Restarting ram node first"):
            self._test_creating_cluster()
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
            for i in range(1, 4):
                run(f"docker exec rabbit{i} rabbitmqctl stop_app")
            with self.assertRaises(Exception):
                # You can see such in log:
                # {{failed_to_cluster_with,[rabbit@rabbit1,rabbit@rabbit2],"Mnesia could not connect to any nodes."},{rabbit,start,[normal,[]]}}
                run("docker exec rabbit3 rabbitmqctl start_app")
            time.sleep(3)
            stdout = run('docker ps --format="{{.Names}}"')[0]
            self.assertNotIn('rabbit3', stdout)                # vm is also down


        with self.subTest("Restarting disc node (not last stopped disc)"):
            self._test_creating_cluster()
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
            for i in range(1, 4):
                run(f"docker exec rabbit{i} rabbitmqctl stop_app")

            with self.assertRaises(TimeoutExpired):
                # restart disc node that is not stopped last
                run("docker exec rabbit1 rabbitmqctl start_app", timeout=30)  # Waiting for Mnesia tables

            run("docker exec rabbit2 rabbitmqctl start_app")
            run("docker exec rabbit3 rabbitmqctl start_app")
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram


        with self.subTest("Restarting disc node (last stopped disc)"):
            self._test_creating_cluster()
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
            for i in range(1, 4):
                run(f"docker exec rabbit{i} rabbitmqctl stop_app")

            # restart node that is stopped last as disc
            run("docker exec rabbit2 rabbitmqctl start_app")
            # the restarting sequence of rabbit1 and rabbit3 does not matter
            run("docker exec rabbit1 rabbitmqctl start_app")
            run("docker exec rabbit3 rabbitmqctl start_app")
            self.assertEqual(get_running_nodes_types(), (2, 1))

    def test_force_boot(self):
        '''
        通常情况下，当关闭整个 RabbitMQ 集群时，重启的第一个节点应该是最后关闭的节点，因为它可以看到其他节点所看不到的事情。
        但是有时会有一些异常情况出现，比如整个集群都掉电而所有节点都认为它不是最后一个关闭的。
        在这种情况下，可以调用 rabbitmqctl force_boot 命令，这就告诉节点*下次*可以无条件地启动节点。
        '''

        self._test_creating_cluster()
        self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
        for i in range(1, 4):
            run(f"docker exec rabbit{i} rabbitmqctl stop_app")

        # Restarting disc node first (first stopped)
        run("docker exec rabbit1 rabbitmqctl force_boot")  # Ensures that the node will start NEXT TIME, even if it was not the last to shut down.
        run("docker exec rabbit1 rabbitmqctl start_app")
        run("docker exec rabbit2 rabbitmqctl start_app")
        run("docker exec rabbit3 rabbitmqctl start_app")
        self.assertEqual(get_running_nodes_types(), (2, 1))

    def test_partition_with_ha(self):
        '''
        rabbit@rabbit1 (channel1)
        queue1 (master)

        rabbit@rabbit3 (channel3)
        queue3 (master)

        ======== Network Partition =======

        rabbit@rabbit2 (channel2)
        queue2 (master)

        '''
        ips, snames = self._test_creating_cluster_on_aws(3)
        channel1 = pika_channel(host=ips['rabbit1'])
        channel2 = pika_channel(host=ips['rabbit2'])
        channel3 = pika_channel(host=ips['rabbit3'])

        queue1 = pika_queue_declare(channel1, 'queue1')
        queue2 = pika_queue_declare(channel2, 'queue2')
        queue3 = pika_queue_declare(channel3, 'queue3')

        run(f"""ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} 'sudo rabbitmqctl set_policy --priority 0 --apply-to queues pl ".*" "{{\\"ha-mode\\": \\"exactly\\", \\"ha-params\\": 2}}"'""")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1", translation=reverse_dict(snames))

        queue1_node, queue1_slave_nodes = get_queue_nodes_info('queue1', host=ips['rabbit1'])
        queue2_node, queue2_slave_nodes = get_queue_nodes_info('queue2', host=ips['rabbit1'])
        queue3_node, queue3_slave_nodes = get_queue_nodes_info('queue3', host=ips['rabbit1'])

        print("Mock network failure ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A INPUT -p tcp --dport 25672 -j DROP # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A OUTPUT -p tcp --dport 25672 -j DROP # rabbit2")
        time.sleep(90)          # wait at least 75s to trigger net_tick_timeout
        print("Mock network restoring ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D INPUT 1 # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D OUTPUT 1 # rabbit2")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1", translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit2", translation=reverse_dict(snames))

        self.assertFalse(channel1.is_closed)
        self.assertFalse(channel2.is_closed)
        self.assertFalse(channel3.is_closed)

        random_str = get_uuid()
        for q in [queue1, queue2, queue3]:
            print(f'Publishing msg {random_str} to {q} on rabbit1')
            pika_simple_publish(channel1, '', q, random_str)
            master, slaves = get_queue_nodes_info(q, host=ips['rabbit2'])
            if master == f'rabbit@{snames["rabbit2"]}':  # 该队列原先在rabbit2上出现过，分区后在rabbit2上升级为master队列
                self.assertIsNone(pika_basic_get(channel2, q))
                self.assertEqual(pika_queue_counters(channel2, q)[1], 0)  # can not see msg from passive declare
                self._wait_until(lambda: get_queue_info(q, ips['rabbit2'])['messages_ready'], 1)  # can see msg from management api
            else:
                self.assertEqual(pika_basic_get(channel2, q), random_str)

        print("Purging all msg ...")
        for q in [queue1, queue2, queue3]:
            pika_queue_purge(channel1, q)
            pika_queue_purge(channel2, q)

        random_str = get_uuid()
        for q in [queue1, queue2, queue3]:
            print(f'Publishing msg {random_str} to {q} on rabbit2')
            pika_simple_publish(channel2, '', q, random_str)
            master, slaves = get_queue_nodes_info(q, host=ips['rabbit2'])
            if master == f'rabbit@{snames["rabbit2"]}':  #
                self.assertIsNone(pika_basic_get(channel1, q))
                self.assertEqual(pika_queue_counters(channel1, q)[1], 0)  # can not see msg from passive declare
                self._wait_until(lambda: get_queue_info(q, ips['rabbit1'])['messages_ready'], 1)  # can see msg from management api
            else:
                self.assertEqual(pika_basic_get(channel1, q), random_str)


    def test_partition_without_ha(self):
        '''
        node1: (channel1)
        queue1
        ======== Network Partition ========
        node2: (channel2)
        queue2
        '''
        ips, snames = self._test_creating_cluster_on_aws(2)
        channel1 = pika_channel(host=ips['rabbit1'])
        channel2 = pika_channel(host=ips['rabbit2'])
        exchange = pika_exchange_declare(channel1, 'exchange')
        queue1 = pika_queue_declare(channel1, 'queue1')
        queue2 = pika_queue_declare(channel2, 'queue2')
        pika_queue_bind(channel1, queue2, exchange, 'rk2')
        pika_queue_bind(channel2, queue1, exchange, 'rk1')

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1", translation=reverse_dict(snames))

        print("Mock network failure ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A INPUT -p tcp --dport 25672 -j DROP # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A OUTPUT -p tcp --dport 25672 -j DROP # rabbit2")
        time.sleep(90)          # wait at least 75s to trigger net_tick_timeout

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
        stdout = run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1",
                     translation=reverse_dict(snames))[0]
        self.assertEqual(get_running_nodes(host=ips['rabbit1']), [f'rabbit@{snames["rabbit1"]}'])
        self.assertNotIn("queue2", stdout)  # queue2 disappeared from node1
        self.assertIsNone(get_queue_info(queue2, ips['rabbit1']))

        # recover network
        print("Recovering network ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D INPUT 1 # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D OUTPUT 1 # rabbit2")

        self.assertFalse(channel1.is_closed)
        self.assertFalse(channel2.is_closed)

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))  # partition detected
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl cluster_status # rabbit2", translation=reverse_dict(snames))  # partition detected
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1",
            translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit2",
            translation=reverse_dict(snames))

        pika_simple_publish(channel2, '', queue1, 'msg1')  # no master pid info for queue1 on rabbit2
        self.assertIsNone(pika_basic_get(channel1, queue1))  # can not be consumed by channel1 of course
        pika_simple_publish(channel2, '', queue2, 'msg2')    # master pid info for queue2 still on rabbit2
        self.assertEqual(pika_basic_get(channel2, queue2), 'msg2')  # can consume messages on channel2 of course



    def test_recovering_from_partition_by_restarting_all_nodes(self):
        '''
        rabbit1 (disc)
        rabbit2 (ram)
        === network partition ===
        rabbit3 (disc)
        rabbit4 (ram)
        '''
        ips, snames = self._test_creating_cluster_on_aws(4, additional_disc_index_list=[3])
        internal_ips = {}
        for node, sname in snames.items():
            internal_ip = sname[3:].replace('-', '.')
            internal_ips[node] = internal_ip
        print(f'internal ips: {internal_ips}')

        channel1 = pika_channel(host=ips['rabbit1'])
        channel2 = pika_channel(host=ips['rabbit2'])
        channel3 = pika_channel(host=ips['rabbit3'])
        channel4 = pika_channel(host=ips['rabbit4'])

        queue1 = pika_queue_declare(channel1, 'queue1', durable=True)
        queue2 = pika_queue_declare(channel2, 'queue2', durable=True)
        queue3 = pika_queue_declare(channel3, 'queue3', durable=True)
        queue4 = pika_queue_declare(channel4, 'queue4', durable=True)

        run(f"""ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} 'sudo rabbitmqctl set_policy --priority 0 --apply-to queues pl ".*" "{{\\"ha-mode\\": \\"all\\"}}"'""")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1", translation=reverse_dict(snames))

        print("Mock network failure ...")
        for ip in [ips['rabbit3'], ips['rabbit4']]:
            for internal_ip in [internal_ips['rabbit1'], internal_ips['rabbit2']]:
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -I INPUT  -s {internal_ip} -j DROP")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -I OUTPUT -d {internal_ip} -j DROP")
        time.sleep(90)          # wait at least 75s to trigger net_tick_timeout
        print("Mock network restoring ...")
        for ip in [ips['rabbit3'], ips['rabbit4']]:
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -D INPUT 1")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -D INPUT 1")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -D OUTPUT 1")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo iptables -D OUTPUT 1")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit1",
            translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo rabbitmqctl list_queues -q name pid slave_pids | column -t # rabbit3",
            translation=reverse_dict(snames))

        self.assertFalse(channel1.is_closed)
        self.assertFalse(channel2.is_closed)
        self.assertFalse(channel3.is_closed)
        self.assertFalse(channel4.is_closed)

        for node, ip in ips.items():
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl stop_app # {node}")

        with self.assertRaises(Exception):
            # "Mnesia could not connect to any nodes." in log
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl start_app # rabbit2")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl start_app # rabbit1")
        # wait until rabbit1 is ready, otherwise startging rabbit2 may fail
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl await_online_nodes 1 # rabbit1")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl start_app # rabbit2")

        new_channel1 = pika_channel(host=ips['rabbit1'])
        pika_simple_publish(new_channel1, '', queue1, "msg in partition1")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo rabbitmqctl start_app # rabbit3")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo rabbitmqctl start_app # rabbit4")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl list_queues -q {QUEUE_INFOS} | column -t # rabbit1",
            translation=reverse_dict(snames))
        # only slave queue1 on rabbit2 is synchronized
        # this is because the default mode for ha-sync-mode is 'manual'
        self.assertEqual(get_queue_info(queue1, ips['rabbit1'])['synchronised_slave_nodes'], [f'rabbit@{snames["rabbit2"]}'])

        new_channel3 = pika_channel(host=ips['rabbit3'])
        # slave queue1 on rabbit3 will sync master from trust partition
        self.assertEqual(pika_basic_get(new_channel3, queue1), 'msg in partition1')
        # now all queue1 slaves are synchronized
        self._wait_until(lambda: len(get_queue_info(queue1, ips['rabbit1'])['synchronised_slave_nodes']), 3)

    def test_recovering_from_partition_by_restarting_nodes_in_untrust_partition(self):
        '''
        rabbit1(disc)
        rabbit3(ram)
        === network partition ===
        rabbit2(ram)
        '''
        ips, snames = self._test_creating_cluster_on_aws(3)
        print("Mock network failure ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A INPUT -p tcp --dport 25672 -j DROP # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -A OUTPUT -p tcp --dport 25672 -j DROP # rabbit2")
        time.sleep(90)          # wait at least 75s to trigger net_tick_timeout
        print("Mock network restoring ...")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D INPUT 1 # rabbit2")
        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D OUTPUT 1 # rabbit2")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1")

        running_nodes_partition1 = get_running_nodes(host=ips['rabbit1'])
        self.assertEqual(len(running_nodes_partition1), 2)
        self.assertIn(f'rabbit@{snames["rabbit1"]}', running_nodes_partition1)
        self.assertIn(f'rabbit@{snames["rabbit3"]}', running_nodes_partition1)

        ips_partition1 = [ips['rabbit1'], ips['rabbit3']]
        for ip in ips_partition1:
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl stop_app")
        for ip in reversed(ips_partition1):  # the order does not matter in fact
            run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl start_app")

        run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1")
        self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 3)


    def test_partition_handling_strategy_pause_minority(self):
        with self.subTest("4 nodes"):
            '''
            Partition1: rabbit1, rabbit2
            Partition2: rabbit3, rabbit4
            '''
            ips, snames = self._test_creating_cluster_on_aws(4)
            for node, ip in ips.items():
                run(f"echo 'cluster_partition_handling = pause_minority' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo systemctl restart rabbitmq-server # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl environment | grep pause_minority # {node}")

            print("Mocking network failure")
            internal_ip_rabbit1 = snames['rabbit1'][3:].replace('-', '.')
            internal_ip_rabbit2 = snames['rabbit2'][3:].replace('-', '.')
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit3")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit4")
            time.sleep(90)          # wait at least 75s to trigger net_tick_timeout
            # The minority nodes will pause as soon as a partition starts
            for node, ip in ips.items():
                with self.assertRaises(Exception) as raised_exception:
                    run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl cluster_status # {node}")
                    self.assertIn("this command requires the 'rabbit' app to be running on the target node",
                                  raised_exception.exception.err_msg)
            print("Mocking network restoration")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -F # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -F # rabbit4")

            time.sleep(10)           # wait for rabbit1 ready
            # Monority node swill start again when the partition ends.
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl await_online_nodes 4 # rabbit1")

        with self.subTest("3 nodes"):
            '''
                     rabbit1
                     /     \
                    /       \
              rabbit2 --x--  rabbit3


            Partition1: rabbit1, rabbit3
            Partition2: rabbit2

            '''
            ips, snames = self._test_creating_cluster_on_aws(3)
            internal_ip_rabbit3 = snames['rabbit3'][3:].replace('-', '.')

            for node, ip in ips.items():
                run(f"echo 'cluster_partition_handling = pause_minority' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo systemctl restart rabbitmq-server # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl environment | grep pause_minority # {node}")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))

            print("Mocking network failure")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -I INPUT -s {internal_ip_rabbit3} -j DROP # rabbit2")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -I OUTPUT -d {internal_ip_rabbit3} -j DROP # rabbit2")
            time.sleep(90)          # wait at least 75s to trigger net_tick_timeout

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
            with self.assertRaises(Exception) as raised_exception:
                run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl cluster_status # rabbit2")
            self.assertIn("this command requires the 'rabbit' app to be running on the target node",
                          raised_exception.exception.err_msg)

            print("Mocking network restoration")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D INPUT 1 # rabbit2")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo iptables -D OUTPUT 1 # rabbit2")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status # rabbit1", translation=reverse_dict(snames))
            self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 3)

    def test_partition_handling_strategy_pause_if_all_down(self):
        '''
        All the listed nodes must be down for RabbitMQ to pause a cluster node.
        This is close to the pause-minority mode, however,
        it allows an administrator to decide which nodes to prefer, instead of relying on the context.
        '''

        with self.subTest('Listed nodes not partitioned'):
            '''
            Partition1: rabbit1(preferred), rabbit2(preferred)
            Partition2: rabbit3, rabbit4
            '''
            ips, snames = self._test_creating_cluster_on_aws(4)
            for node, ip in ips.items():
                run(f"echo 'cluster_partition_handling = pause_if_all_down' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.recover = ignore' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.1 = rabbit@{snames['rabbit1']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.2 = rabbit@{snames['rabbit2']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo systemctl restart rabbitmq-server # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl environment | grep pause_if_all_down # {node}")

            print("Mocking network failure")
            internal_ip_rabbit1 = snames['rabbit1'][3:].replace('-', '.')
            internal_ip_rabbit2 = snames['rabbit2'][3:].replace('-', '.')
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit3")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit4")
            time.sleep(90)          # wait at least 75s to trigger net_tick_timeout

            for node, ip in ips.items():
                if node in ['rabbit3', 'rabbit4']:
                    with self.assertRaises(Exception) as raised_exception:
                        run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl cluster_status # {node}")
                        self.assertIn("this command requires the 'rabbit' app to be running on the target node",
                                      raised_exception.exception.err_msg)
                else:           # rabbit1 or rabbit2 (if mode is pause-minority, rabbit1 and rabbit2 will also be paused)
                    self.assertEqual(len(get_running_nodes(host=ip)), 2)

        with self.subTest('Listed nodes partitioned'):
            '''
            Partition1: rabbit1, rabbit2(preferred)
            Partition2: rabbit3(preferred), rabbit4
            '''
            ips, snames = self._test_creating_cluster_on_aws(4)
            for node, ip in ips.items():
                run(f"echo 'cluster_partition_handling = pause_if_all_down' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.recover = ignore' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.1 = rabbit@{snames['rabbit2']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.2 = rabbit@{snames['rabbit3']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo systemctl restart rabbitmq-server # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl environment | grep pause_if_all_down # {node}")

            print("Mocking network failure")
            internal_ip_rabbit1 = snames['rabbit1'][3:].replace('-', '.')
            internal_ip_rabbit2 = snames['rabbit2'][3:].replace('-', '.')
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit3")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit4")
            time.sleep(90)          # wait at least 75s to trigger net_tick_timeout

            for node, ip in ips.items():
                # No node will pause.
                # Thit is why there is an additional ignore/autoheal argument (pause_if_all_down.recover) to indicate how to recover from the partition.
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl cluster_status # {node}")
            self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 2)
            self.assertEqual(len(get_running_nodes(host=ips['rabbit3'])), 2)

            print("Mocking network restoration")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -F # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -F # rabbit4")
            time.sleep(10)
            self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 2)  # becaus pause_if_all_down.recover = ignoree

        with self.subTest('Listed nodes partitioned and autoheal when recovering'):
            '''
            Partition1: rabbit1, rabbit2(preferred)
            Partition2: rabbit3(preferred), rabbit4
            '''
            ips, snames = self._test_creating_cluster_on_aws(4)
            for node, ip in ips.items():
                run(f"echo 'cluster_partition_handling = pause_if_all_down' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.recover = autoheal' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.1 = rabbit@{snames['rabbit2']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"echo 'cluster_partition_handling.pause_if_all_down.nodes.2 = rabbit@{snames['rabbit3']}' | ssh {SSH_OPTIONS} ec2-user@{ip} sudo tee -a /etc/rabbitmq/rabbitmq.conf # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo systemctl restart rabbitmq-server # {node}")
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl environment | grep pause_if_all_down # {node}")

            print("Mocking network failure")
            internal_ip_rabbit1 = snames['rabbit1'][3:].replace('-', '.')
            internal_ip_rabbit2 = snames['rabbit2'][3:].replace('-', '.')
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit3")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit1} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I INPUT  -s {internal_ip_rabbit2} -j DROP # rabbit4")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -I OUTPUT -d {internal_ip_rabbit2} -j DROP # rabbit4")
            time.sleep(90)          # wait at least 75s to trigger net_tick_timeout

            for node, ip in ips.items():
                # No node will pause.
                # Thit is why there is an additional ignore/autoheal argument (pause_if_all_down.recover) to indicate how to recover from the partition.
                run(f"ssh {SSH_OPTIONS} ec2-user@{ip} sudo rabbitmqctl cluster_status # {node}")
            self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 2)
            self.assertEqual(len(get_running_nodes(host=ips['rabbit3'])), 2)

            print("Mocking network restoration")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit3']} sudo iptables -F # rabbit3")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit4']} sudo iptables -F # rabbit4")
            time.sleep(10)
            self.assertEqual(len(get_running_nodes(host=ips['rabbit1'])), 4)




    def test_forget_cluster_node(self):
        '''
        如果最后一个关闭的节点永久丢失了，可以使用 rabbitmqctl forget_cluster_node 命令（优先于 force_boot ），因为它可以确保镜像队列的正常运转。
        使用 forget_cluster_node 命令的话，需要删除的节点必须是 offline ，执行命令的节点必须 online ，（否则需要指定 --offline 参数）。
        注意：如果指定执行命令的节点为 --offline ，意味着不能存在 Erlang node ，因为 rabbitmqctl 需要 mock 一个同名的 node 。
        '''
        with self.subTest("When current node online"):
            self._test_creating_cluster()
            self.assertEqual(get_running_nodes_types(), (2, 1))  # 2 disc, 1 ram
            run("docker exec rabbit2 rabbitmqctl stop_app")
            run("docker exec rabbit1 rabbitmqctl forget_cluster_node rabbit@rabbit2")
            self.assertEqual(get_running_nodes_types(), (1, 1))


        with self.subTest("When current node offline"):
            ips, snames = self._test_creating_cluster_on_aws(3, [3])
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl cluster_status")
            self.assertEqual(get_running_nodes_types(host=ips['rabbit1']), (2, 1))  # rabbit1 and rabbit3 are disc

            for i in range(1, 4):
                k = f'rabbit{i}'
                run(f"ssh {SSH_OPTIONS} ec2-user@{ips[k]} sudo rabbitmqctl stop_app # on {k}")

            with self.assertRaises(Exception) as raised_exception:
                run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl forget_cluster_node --offline rabbit@{snames['rabbit3']} # forget rabbit3 (on rabbit1)")
            self.assertIn('this command requires the target node to be stopped', raised_exception.exception.err_msg)
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo systemctl stop rabbitmq-server # on rabbit1")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo rabbitmqctl forget_cluster_node --offline rabbit@{snames['rabbit3']} # forget rabbit3 (on rabbit1)")

            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit1']} sudo systemctl start rabbitmq-server # on rabbit1")
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl start_app # on rabbit2")
            self.assertEqual(get_running_nodes_types(host=ips['rabbit1']), (1, 1))
            self.assertEqual(get_running_nodes_types(host=ips['rabbit2']), (1, 1))
            run(f"ssh {SSH_OPTIONS} ec2-user@{ips['rabbit2']} sudo rabbitmqctl cluster_status # on rabbit2")



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
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_a --name rabbit_a -p 15672:15672 -p 5672:5672 rabbitmq:{RABBITMQ_VERSION}-management')
        run('docker exec rabbit_a rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')

        # rabbit_b
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_b --name rabbit_b -p 15673:15672 -p 5673:5672 rabbitmq:{RABBITMQ_VERSION}-management')
        run('docker exec rabbit_b rabbitmqctl wait /var/lib/rabbitmq/mnesia/rabbit.pid')
        run('docker exec rabbit_b rabbitmqctl stop_app')
        run('docker exec rabbit_b rabbitmqctl reset')
        run('docker exec rabbit_b rabbitmqctl join_cluster --ram rabbit@rabbit_a')
        run('docker exec rabbit_b rabbitmqctl start_app')
        self.assertEqual(get_running_nodes_types(), (1, 1))

        run('docker exec rabbit_a rabbitmqctl stop_app')  # rabbit_a offline

        # rabbit_c
        run(f'docker run {BASIC_DOCKER_OPTS} --hostname rabbit_c --name rabbit_c -p 15674:15672 -p 5674:5672 rabbitmq:{RABBITMQ_VERSION}-management')
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

if __name__ == '__main__':
    unittest.main(verbosity=2)