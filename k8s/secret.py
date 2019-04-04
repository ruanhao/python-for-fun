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
        run('kubectl delete secret fortune-https', True)
        run('kubectl delete secret fortune-https-tls', True)

        run('openssl genrsa -out https.key 2048')
        run('openssl req -new -x509 -key https.key -out https.cert -days 3650 -subj /CN=www.kubia-example.com')
        run('echo bar > foo')

        run('kubectl create secret generic fortune-https --from-file=https.key --from-file=https.cert --from-file=foo')
        run('kubectl create secret tls fortune-https-tls --cert=https.cert --key=https.key')
        run('kubectl get secret fortune-https -o yaml')
        run('kubectl get secret fortune-https-tls -o yaml')


    def test_using_secret_by_vol(self):
        run("kubectl delete pod fortune-https", True)
        ensure_pod_phase('fortune-https', 'Deleted')
        run('kubectl delete cm fortune-config', True)

        # 1, create cm needed
        run('kubectl create configmap fortune-config --from-file=configmap-https-files')

        # 2, create pod
        run('kubectl create -f fortune-pod-https.yaml')
        ensure_pod_phase('fortune-https', 'Running')

        # verify
        p = subprocess.Popen('kubectl port-forward fortune-https 8443:443', shell=True)
        time.sleep(1)
        run('curl -v -s -k https://localhost:8443')
        p.terminate()
        # The secret volume uses an in-memory filesystem (tmpfs) for the Secret files.
        run("kubectl exec fortune-https -c web-server -- mount | grep certs")
