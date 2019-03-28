#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
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

    def test_labels(self):
        run('kubectl get po --show-labels')
        # only interested in certain labels
        run('kubectl get po -L creation_method,env')

        # modify labels of existing pods
        # need to use the --overwrite option when changing existing labels.
        run('kubectl label po kubia-manual creation_method=manual --overwrite')
        run('kubectl label po kubia-manual-v2 env=debug --overwrite')
        run('kubectl get po -L creation_method,env')
