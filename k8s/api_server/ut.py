#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
import json
import yaml
from k8s_utils import run
from k8s_utils import ensure_pod_phase
from k8s_utils import ensure_namespace_phase
from contextlib import redirect_stdout
from contextlib import redirect_stderr

class UnitTest(unittest.TestCase):


    def test_accessing_api_server_with_ambassador_container(self):
        run('kubectl delete pod curl-with-ambassador', True)
        ensure_pod_phase('curl-with-ambassador', 'Deleted')

        run('kubectl create -f curl-with-ambassador.yaml')
        ensure_pod_phase('curl-with-ambassador', 'Running')
        run('kubectl apply -f fabric8-rbac.yaml', True)
        run('kubectl exec curl-with-ambassador -c main -- curl -s localhost:8001')
        run('kubectl delete -f fabric8-rbac.yaml', True)


    def test_create_service_account(self):
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


    def test_rbac_with_role_and_rolebinding(self):
        '''
        minikube start --extra-config=apiserver.authorization-mode=RBAC
        '''
        run('kubectl delete ns foo', True)
        run('kubectl delete ns bar', True)
        ensure_namespace_phase('foo', 'Deleted')
        ensure_namespace_phase('bar', 'Deleted')


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


        # These two Roles will allow you to list Services in the foo and bar namespaces from within your two pods
        run('kubectl create -f service-reader.yaml -n foo')  # create role in namespace foo
        # Instead of creating the Role from a YAML file, you could also create it with the special kubectl create role command
        run('kubectl create role service-reader --verb=get --verb=list --resource=services -n bar')

        # Binding Role to ServiceAccount
        run('kubectl create rolebinding test --role=service-reader --serviceaccount=foo:default -n foo')

        # now it is ok
        stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/foo/services")
        self.assertEqual(json.loads(stdout)['kind'], "ServiceList")

        with self.subTest("Including serviceaccounts from other namespaces in a rolebinding"):
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



    def test_rbac_with_cluster_role_and_rolebinding(self):
        run('kubectl delete clusterrole pv-reader', True)
        run('kubectl delete clusterrolebinding pv-test', True)
        run('kubectl delete clusterrolebinding view-test', True)
        run('kubectl delete ns foo', True)
        run('kubectl delete ns bar', True)
        ensure_namespace_phase('foo', 'Deleted')
        ensure_namespace_phase('bar', 'Deleted')
        run('kubectl create ns foo', True)
        run('kubectl create ns bar', True)
        run('kubectl run test --image=luksa/kubectl-proxy -n foo')
        run('kubectl run test --image=luksa/kubectl-proxy -n bar')
        pod_name = run("kubectl get pod -n foo -o jsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name, expected_phase='Running', ns='foo')


        with self.subTest("Allowing access to cluster-level resources"):
            # the default ServiceAccount can’t list PersistentVolumes.
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/persistentvolumes", True)
            self.assertEqual(json.loads(stdout)['code'], 403)

            run('kubectl create clusterrole pv-reader --verb=get,list --resource=persistentvolumes')
            run('kubectl create rolebinding pv-test --clusterrole=pv-reader --serviceaccount=foo:default -n foo')

            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/persistentvolumes", True)
            self.assertEqual(json.loads(stdout)['code'], 403)  # must use ClusterRoleBinding to grant access to cluster-level resources

            run('kubectl create clusterrolebinding pv-test --clusterrole=pv-reader --serviceaccount=foo:default')
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/persistentvolumes")
            self.assertEqual(json.loads(stdout)['kind'], "PersistentVolumeList")

        with self.subTest("Allowing access to non-resource URLs"):
            '''
            API server also exposes non-resource URLs.
            Access to these URLs must also be granted explicitly; otherwise the API server will reject the client’s request.
            Usually, this is done for you automatically through the system:discovery ClusterRole and the identically named ClusterRoleBinding.
            '''
            minikube_ip = run('minikube ip', True)
            # making request as an unauthenticated user
            run(f'curl https://{minikube_ip}:8443/api -k -s')

        with self.subTest("Using clusterroles to grant access to resources in specific namespaces"):
            '''
            ClusterRoles don’t always need to be bound with cluster-level ClusterRoleBindings.
            They can also be bound with regular, namespaced RoleBindings.

            1. If you create a ClusterRoleBinding and reference the ClusterRole in it,
               the subjects listed in the binding can view the specified resources across all namespaces.
            2. If, on the other hand, you create a RoleBinding,
               the subjects listed in the binding can only view resources in the namespace of the RoleBinding.
            '''

            # case 1
            run('kubectl create clusterrolebinding view-test --clusterrole=view --serviceaccount=foo:default')
            # view pods in namespace foo
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/foo/pods")
            self.assertEqual(json.loads(stdout)['kind'], "PodList")
            # view pods in namespace bar
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/bar/pods")
            self.assertEqual(json.loads(stdout)['kind'], "PodList")
            # retrieve pods across all namespaces
            run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/pods")

            # case 2
            run('kubectl delete clusterrolebinding view-test')
            run('kubectl create rolebinding view-test --clusterrole=view --serviceaccount=foo:default -n foo')
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/foo/pods")
            self.assertEqual(json.loads(stdout)['kind'], "PodList")
            stdout = run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/namespaces/bar/pods")
            self.assertEqual(json.loads(stdout)['code'], 403)
            run(f"kubectl exec {pod_name} -n foo -- curl -s localhost:8001/api/v1/pods")
            self.assertEqual(json.loads(stdout)['code'], 403)
