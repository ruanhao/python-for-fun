#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase, ensure_namespace_phase
import time
import subprocess


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
