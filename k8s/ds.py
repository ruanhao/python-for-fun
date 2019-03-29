#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
import json

class UnitTest(unittest.TestCase):


    def test_create(self):
        run('kubectl delete ds ssd-monitor', True)
        run('kubectl label node minikube disk=hhd --overwrite')
        run('kubectl create -f ssd-monitor-daemonset.yaml')
        ret0 = json.loads(run('kubectl get ds ssd-monitor -o json', True))
        self.assertEqual(ret0['status']['currentNumberScheduled'], 0)
        run('kubectl label node minikube disk=ssd --overwrite')
        ret1 = json.loads(run('kubectl get ds ssd-monitor -o json', True))
        self.assertNotEqual(ret1['status']['currentNumberScheduled'], 0)

        with self.subTest("Removing required label from node"):
            run('kubectl label node minikube disk=hhd --overwrite')
            ret2 = json.loads(run('kubectl get ds ssd-monitor -o json', True))
            self.assertEqual(ret2['status']['currentNumberScheduled'], 0)
