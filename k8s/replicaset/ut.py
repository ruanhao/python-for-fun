#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import init_test_env
from k8s_utils import ensure_rc_ready
import time
import json

NS = 'rs-test'

class UnitTest(unittest.TestCase):


    def test_create(self):
        init_test_env(NS)
        run(f'kubectl create -f kubia-replicaset.yaml -n {NS}')
        run(f'kubectl get rs -n {NS}')
        run(f'kubectl get pods --show-labels -n {NS}')

    def test_pods_keeping_crashing(self):
        '''
        The ReplicaSet controller doesn't care if the pods are dead.
        All it cares about is that THE NUMBER OF PODS matches the desired replica count.
        '''
        init_test_env(NS)
        run(f'kubectl create -f replicaset-crashingpods.yaml -n {NS}')
        run(f'kubectl describe rs crashing-pods -n {NS} | grep "Pods Status\|Replicas"')
