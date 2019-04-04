#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase

class UnitTest(unittest.TestCase):


    def test_accessing_api_server_with_ambassador_container(self):
        run('kubectl delete pod curl-with-ambassador', True)
        ensure_pod_phase('curl-with-ambassador', 'Deleted')

        run('kubectl create -f curl-with-ambassador.yaml')
        ensure_pod_phase('curl-with-ambassador', 'Running')
        run('kubectl apply -f fabric8-rbac.yaml', True)
        run('kubectl exec curl-with-ambassador -c main -- curl -s localhost:8001')
        run('kubectl delete -f fabric8-rbac.yaml', True)
