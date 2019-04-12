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

    def test_creating_pod_with_resource_requested(self):
        init_test_env(NS)
        run(f'kubectl create -f requests-pod.yaml -n {NS}')
        ensure_pod_phase('requests-pod', 'Running', NS)
        # The Minikube VM, which is where this example is running, has two CPU cores allotted to it.
        # That's why the process is shown consuming 50% of the whole CPU.
        run(f'kubectl exec requests-pod -n {NS} -- top -bn1')


        with self.subTest("Creating a pod that doesn't fit on any node"):
            run(f"kubectl run requests-pod-2 --image=busybox --restart Never --requests='cpu=800m,memory=20Mi' -n {NS} -- dd if=/dev/zero of=/dev/null")
            ensure_pod_phase('requests-pod-2', 'Running', NS)
            time.sleep(5)
            run(f"kubectl run requests-pod-3 --image=busybox --restart Never --requests='cpu=1,memory=20Mi' -n {NS} -- dd if=/dev/zero of=/dev/null")
            ensure_pod_phase('requests-pod-3', 'Pending', NS)
            stdout = run(f"kubectl get po requests-pod-3 -n {NS} -o jsonpath='{{.status.conditions[0].message}}'")
            self.assertIn("Insufficient cpu", stdout)
            run(f'kubectl delete po requests-pod-2 -n {NS}')
            ensure_pod_phase('requests-pod-2', 'Deleted', NS)
            ensure_pod_phase('requests-pod-3', 'Running', NS)
            # Remember to clean up when this test is finished, it makes cpu crazy


    def test_creating_pod_with_resource_limited(self):
        init_test_env(NS)
        run(f'kubectl create -f limited-pod.yaml -n {NS}')
        ensure_pod_phase('limited-pod', 'Running', NS)
        cpu_period = int(run(f'kubectl exec limited-pod -n {NS} -- cat /sys/fs/cgroup/cpu/cpu.cfs_period_us'))
        cpu_quota = int(run(f'kubectl exec limited-pod -n {NS} -- cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us'))
        minikube_cpus = 2
        self.assertEqual(cpu_quota/cpu_period/minikube_cpus, 0.1)  # 最多能使用 10% CPU
