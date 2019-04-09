#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import json
import yaml
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


    def test_rbac(self):
        run('kubectl delete ns foo', True)
        run('kubectl delete ns bar', True)


        run('kubectl create ns foo')
        # luksa/kubectl-proxy will run the proxy which will take care of authentication and HTTPS,
        # so you can focus on the authorization aspect of API server security.
        run('kubectl run test --image=luksa/kubectl-proxy -n foo')

        run('kubectl create ns bar')
        run('kubectl run test --image=luksa/kubectl-proxy -n bar')

        pod_name = run("kubectl get pod -n foo -o jsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name, expected_phase='Running', ns='foo')
        stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/foo/services")
        # The default permissions for a ServiceAccount don't allow it to list or modify any resources.
        self.assertEqual(json.loads(stdout)['code'], 403)

        with self.subTest("Role and RoleBinding"):
            # These two Roles will allow you to list Services in the foo and bar namespaces from within your two pods
            run('kubectl create -f service-reader.yaml -n foo')  # create role in namespace foo
            # Instead of creating the Role from a YAML file, you could also create it with the special kubectl create role command
            run('kubectl create role service-reader --verb=get --verb=list --resource=services -n bar')

            # Binding Role to ServiceAccount
            run('kubectl create rolebinding test --role=service-reader --serviceaccount=foo:default -n foo')

            # now it is ok
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/foo/services")
            self.assertEqual(json.loads(stdout)['kind'], "ServiceList")

            run('kubectl get rolebindings test -o yaml -n foo')  # before modification
            json_def = json.loads(run('kubectl get rolebindings test -o json -n foo', True))
            json_def['subjects'][0]['namespace'] = 'bar'
            with open('/tmp/bind_service_account_from_other_namespace.yaml', 'wb') as fp:
                fp.write(yaml.dump(json_def).encode('utf-8'))
            run('kubectl replace -f /tmp/bind_service_account_from_other_namespace.yaml -n foo')
            run('kubectl get rolebindings test -o yaml -n foo')  # after modification
            # verify
            bar_pod_name = run("kubectl get pod -n bar -o jsonpath='{.items[0].metadata.name}'", True)
            ensure_pod_phase(bar_pod_name, expected_phase='Running', ns='bar')
            # can see service in foo namespace
            stdout = run(f"kubectl exec {bar_pod_name} -n bar -- curl -s localhost:8001/api/v1/namespaces/foo/services")
            self.assertEqual(json.loads(stdout)['kind'], "ServiceList")
