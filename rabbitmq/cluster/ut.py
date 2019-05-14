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

class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")


    def test_creating_cluster(self):
        run('docker stop `docker ps --format="{{.Names}}"`', True)
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
