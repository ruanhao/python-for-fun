#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
from k8s_utils import ensure_namespace_phase
from k8s_utils import get_pod_phase
from k8s_utils import init_test_env
import time
import subprocess

NS = "computational-resource-test"


class UnitTest(unittest.TestCase):

    def test_creating_pod_with_request_resource(self):
        init_test_env(NS)
        run(f'kubectl create -f requests-pod.yaml -n {NS}')
        ensure_pod_phase('requests-pod', 'Running', NS)
        # The Minikube VM, which is where this example is running, has two CPU cores allotted to it.
        # That's why the process is shown consuming 50% of the whole CPU.
        run(f'kubectl exec requests-pod -n {NS} -- top -bn1')
        run(f"kubectl run requests-pod-2 --image=busybox --restart Never --requests='cpu=800m,memory=20Mi' -n {NS} -- dd if=/dev/zero of=/dev/null")
        ensure_pod_phase('requests-pod-2', 'Running', NS)
        time.sleep(5)

        with self.subTest("Creating a pod that doesn't fit on any node"):
            run(f"kubectl run requests-pod-3 --image=busybox --restart Never --requests='cpu=1,memory=20Mi' -n {NS} -- dd if=/dev/zero of=/dev/null")
            stdout = run(f"kubectl get po requests-pod-3 -n {NS} -o jsonpath='{{.status.conditions[0].message}}'")
            self.assertIn("Insufficient cpu", stdout)
