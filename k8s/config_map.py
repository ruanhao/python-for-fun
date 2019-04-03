#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
import subprocess
import time
import json

class UnitTest(unittest.TestCase):


    def test_create(self):
        '''
        Run this tc first
        '''
        run('kubectl delete cm fortune-config', True)
        run('kubectl create -f fortune-config.yaml')
        run('kubectl get cm')
        run('kubectl describe cm fortune-config')


    def test_using_config_map_as_env(self):
        run('kubectl delete pod fortune-env-from-configmap', True)
        ensure_pod_phase('fortune-env-from-configmap', 'Deleted')

        run('kubectl create -f fortune-pod-env-configmap.yaml')
        ensure_pod_phase('fortune-env-from-configmap', 'Running')
        ret = run("kubectl exec fortune-env-from-configmap -c html-generator  -- bash -c 'echo $INTERVAL'")
        self.assertEqual(25, int(ret))


    def test_using_config_map_as_volume(self):
        run('kubectl delete cm fortune-config', True)
        run('kubectl delete pod fortune-configmap-volume', True)
        ensure_pod_phase('fortune-configmap-volume', 'Deleted')

        # 1, Create cm
        run('kubectl create configmap fortune-config --from-file=configmap-files')
        run('kubectl get configmap fortune-config -o yaml')
        # 2, Create pod
        run('kubectl create -f fortune-pod-configmap-volume.yaml')
        ensure_pod_phase('fortune-configmap-volume', 'Running')

        # 3, Verify
        p = subprocess.Popen('kubectl port-forward fortune-configmap-volume 8888:80', shell=True)
        time.sleep(1)
        run('curl -s -H "Accept-Encoding: gzip" -I localhost:8888')
        p.terminate()
        run('kubectl exec fortune-configmap-volume -c web-server ls /etc/nginx/conf.d')
        run("kubectl exec fortune-configmap-volume -c html-generator -- bash -c 'echo $INTERVAL'")

        with self.subTest("Exposing Certain ConfigMap Entries in the Volume"):
            run('kubectl delete pod fortune-configmap-volume-with-items', True)
            ensure_pod_phase('fortune-configmap-volume-with-items', 'Deleted')

            run('kubectl create -f fortune-pod-configmap-volume-with-items.yaml')
            ensure_pod_phase('fortune-configmap-volume-with-items', 'Running')
            run('kubectl exec fortune-configmap-volume-with-items -c web-server ls /etc/nginx/conf.d')  # only one file
