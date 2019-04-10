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

NAME_SPACE = "pod-test"


class UnitTest(unittest.TestCase):

    def test_utils(self):
        run('kubectl explain pods')
        run('kubectl explain pods.spec.containers.image')


    def test_create(self):
        '''
        Please run this testcase at first
        '''
        run('kubectl create -f kubia-manual.yaml')
        run('kubectl create -f kubia-manual-with-labels.yaml')

    def test_log(self):
        # Container logs are automatically rotated daily and every time the log file reaches 10MB in size.
        # The kubectl logs command only shows the log entries from the last rotation.
        run('kubectl logs kubia-manual')
        # specify container name
        run('kubectl logs kubia-manual -c kubia')

    def test_forword_local_port(self):
        p = subprocess.Popen('kubectl port-forward kubia-manual 8888:8080', shell=True)
        time.sleep(1)
        run('curl -Ss localhost:8888')
        p.terminate()

    def test_annotation(self):
        # It’s a good idea to use this format for annotation keys to prevent key collisions.
        run('kubectl annotate pod kubia-manual mycompany.com/someannotation="foo bar"')
        run('kubectl describe pod kubia-manual | grep Annotations')

    def test_liveness_probe(self):
        if get_pod_phase('kubia-liveness') != 'Running':
            run('kubectl delete po kubia-liveness', True)
            ensure_pod_phase('kubia-liveness', 'Deleted')
            run('kubectl create -f kubia-liveness-probe.yaml', True)
            ensure_pod_phase('kubia-liveness')




    def test_namespace(self):
        run('kubectl get po -n kube-system')
        with self.subTest("Creating ns"):
            run('kubectl delete namespace custom-namespace', True)
            ensure_namespace_phase('custom-namespace', 'Deleted')
            run('kubectl create -f custom-namespace.yaml')  # also: kubectl create namespace <your-namespace>
            run('kubectl get ns')

        with self.subTest("Creating pod in other namespace"):
            run('kubectl create -f kubia-manual.yaml -n custom-namespace')
            run('kubectl get po -n custom-namespace')




    def test_labels(self):
        run('kubectl get po --show-labels')
        # only interested in certain labels
        run('kubectl get po -L creation_method,env')

        with self.subTest("Modifying labels"):
            # modify labels of existing pods
            # need to use the --overwrite option when changing existing labels.
            run('kubectl label po kubia-manual creation_method=manual --overwrite')
            run('kubectl label po kubia-manual-v2 env=debug --overwrite')
            run('kubectl get po -L creation_method,env')

        with self.subTest('Listing pods using a label selector'):
            run('kubectl get po -l creation_method=manual --show-labels')
            # list all pods that include the 'env' label
            run('kubectl get po -l env --show-labels')
            # list those that don’t have the 'env' label
            run("kubectl get po -l '!env' --show-labels")
            # select pods with the 'creation_method' label with any value other than 'manual'
            run("kubectl get po -l 'creation_method!=manual' --show-labels")
            # select pods with the 'env' label set to either 'debug' or 'devel'
            run('kubectl get po -l "env in (debug,devel)" --show-labels')
            # select pods with the 'env' label not set to either 'prod' or 'devel'
            run('kubectl get po -l "env notin (prod,devel)" --show-labels')

        with self.subTest('Scheduling pods to specific nodes'):
            run('kubectl delete pod kubia-gpu', True)  # cleanup first
            ensure_pod_phase('kubia-gpu', 'Deleted')

            time.sleep(10)
            run('kubectl label node minikube gpu=true --overwrite')
            run('kubectl get node -L gpu')
            run('kubectl create -f kubia-gpu.yaml')


    def test_using_host_node_namespaces(self):
        init_test_env(NAME_SPACE)

        with self.subTest("Using node network namespace"):
            run(f'kubectl create -f pod-with-host-network.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-host-network', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-with-host-network -n {NAME_SPACE} -- ifconfig')
            self.assertIn('docker0', stdout)


        with self.subTest("Binding host port without using host network namespace"):
            run(f'kubectl create -f kubia-hostport.yaml -n {NAME_SPACE}')
            ensure_pod_phase('kubia-hostport', "Running", NAME_SPACE)
            minikube_ip = run('minikube ip', True)
            run(f'curl -s http://{minikube_ip}:9000/')


        with self.subTest("Using node PID and IPC namespaces"):
            run(f'kubectl create -f pod-with-host-pid-and-ipc.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-with-host-pid-and-ipc', 'Running', NAME_SPACE)
            run(f'kubectl exec pod-with-host-pid-and-ipc -n {NAME_SPACE} -- ps aux')


    def test_configuring_container_security_context(self):
        init_test_env(NAME_SPACE)
        run(f'kubectl run pod-with-defaults --image alpine --restart Never --namespace {NAME_SPACE} -- /bin/sleep 999999')
        ensure_pod_phase("pod-with-defaults", 'Running', NAME_SPACE)

        with self.subTest("Running a container as a specific user"):
            run(f'kubectl create -f pod-as-user-guest.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-as-user-guest', 'Running', NAME_SPACE)
            stdout = run(f'kubectl exec pod-as-user-guest -n {NAME_SPACE} -- id -u')
            self.assertEqual(stdout, '405')

        with self.subTest("Running container in privileged mode"):
            run(f'kubectl create -f pod-privileged.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-privileged', 'Running', NAME_SPACE)
            stdout1 = run(f'kubectl exec pod-with-defaults -n {NAME_SPACE} -- ls /dev')
            stdout2 = run(f'kubectl exec pod-privileged -n {NAME_SPACE} -- ls /dev')
            # the privileged container sees all the host node's devices. This means it can use any device freely.
            self.assertGreater(len(stdout2.split()), len(stdout1.split()))

        with self.subTest("Adding individual kernel capabilities to a container"):
            stdout = run(f'kubectl exec pod-with-defaults -n {NAME_SPACE} -- date -s "12:00:00" 2>&1')
            self.assertIn("can't", stdout)
            run(f'kubectl create -f pod-add-settime-capability.yaml -n {NAME_SPACE}')
            ensure_pod_phase('pod-add-settime-capability', 'Running', NAME_SPACE)
            run(f'kubectl exec pod-add-settime-capability -n {NAME_SPACE} -- date +%T -s "12:00:00"')
            stdout = run(f'kubectl exec pod-add-settime-capability -n {NAME_SPACE} -- date +%T')
            self.assertIn('12:00:0', stdout)
            run('minikube ssh date')  # node date will be changed, but it can be changed back quickly due to NTP.
