#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
from k8s_utils import ensure_namespace_phase
from k8s_utils import get_pod_phase
from k8s_utils import init_test_env
import time
import yaml
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


    def test_limit_range(self):
        init_test_env(NS)

        with self.subTest("Enforcing limits"):
            run(f'kubectl create -f limits.yaml -n {NS}')
            stdout = run(f'kubectl create -f limits-pod-too-big.yaml -n {NS} 2>&1; true')
            self.assertIn('must be less than or equal to cpu limit', stdout)

        with self.subTest("Applying default resource requests and limits"):
            run(f'kubectl create -f kubia-manual.yaml -n {NS}')
            ensure_pod_phase('kubia-manual', 'Running', NS)
            default_cpu_request = run(f"kubectl get po kubia-manual -n {NS} -o jsonpath='{{.spec.containers[0].resources.requests.cpu}}'")
            default_cpu_limit = run(f"kubectl get po kubia-manual -n {NS} -o jsonpath='{{.spec.containers[0].resources.limits.cpu}}'")
            default_mem_request = run(f"kubectl get po kubia-manual -n {NS} -o jsonpath='{{.spec.containers[0].resources.requests.memory}}'")
            default_mem_limit = run(f"kubectl get po kubia-manual -n {NS} -o jsonpath='{{.spec.containers[0].resources.limits.memory}}'")
            with open('limits.yaml', 'rb') as fp:
                definition = yaml.load(fp, Loader=yaml.Loader)
                container_limits = [limit for limit in definition['spec']['limits'] if limit['type'] == 'Container'][0]
            self.assertEqual(default_cpu_request, container_limits['defaultRequest']['cpu'])
            self.assertEqual(default_cpu_limit, container_limits['default']['cpu'])
            self.assertEqual(default_mem_request, container_limits['defaultRequest']['memory'])
            self.assertEqual(default_mem_limit, container_limits['default']['memory'])

    def test_resource_quota(self):
        init_test_env(NS)

        run(f'kubectl create -f quota-cpu-memory.yaml -n {NS}')
        run(f'kubectl describe quota -n {NS}')

        # when creating a ResourceQuota is that you will also want to create a LimitRange object alongside it.
        stdout = run(f'kubectl create -f kubia-manual.yaml -n {NS} 2>&1; true')
        self.assertIn('must specify limits.cpu,limits.memory,requests.cpu,requests.memory', stdout)
        run(f'kubectl create -f limits.yaml -n {NS}')
        run(f'kubectl create -f kubia-manual.yaml -n {NS}')
        # So having a LimitRange with defaults for those resources can make life a bit easier for people creating pods.
        ensure_pod_phase('kubia-manual', 'Running', NS)
