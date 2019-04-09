#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
from k8s_utils import run
from k8s_utils import ensure_pod_phase
from contextlib import redirect_stdout
from contextlib import redirect_stderr

class UnitTest(unittest.TestCase):

    '''
    minikube start --extra-config=apiserver.authorization-mode=RBAC
    '''


    def test_create(self):
        run('kubectl delete serviceaccount foo', True)
        run('kubectl create serviceaccount foo')
        run('kubectl describe sa foo')
        sec = run("kubectl get sa foo -o jsonpath='{.secrets[0].name}'", True)
        run(f'kubectl describe secret {sec}')

    def test_assigning_sa_to_pod(self):
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_create()

        run('kubectl delete po curl-custom-sa', True)
        ensure_pod_phase('curl-custom-sa', 'Deleted')
        run('kubectl create -f curl-custom-sa.yaml')
        ensure_pod_phase('curl-custom-sa', 'Running')
        sec = run("kubectl get sa foo -o jsonpath='{.secrets[0].name}'", True)
        sec_token = run(f"kubectl get secret {sec} -o jsonpath='{{.data.token}}' | base64 -D")
        pod_token = run("kubectl exec curl-custom-sa -c main -- cat /var/run/secrets/kubernetes.io/serviceaccount/token")
        self.assertEqual(sec_token, pod_token)
        # If the response is Success, this may be because your cluster doesn’t use the RBAC authorization plugin,
        # or you gave all ServiceAccounts full permissions, like:
        # `kubectl create clusterrolebinding permissive-binding --clusterrole=cluster-admin --group=system:serviceaccounts`
        run("kubectl exec curl-custom-sa -c main -- curl -s localhost:8001/api/v1/pods")
