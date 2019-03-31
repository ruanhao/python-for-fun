#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import is_rc_ready
from k8s_utils import ensure_rc_ready
from k8s_utils import ensure_pod_phase
import json
import yaml                     # pip3 install pyyaml

class UnitTest(unittest.TestCase):


    def test_create(self):
        if not is_rc_ready('kubia'):
            run('kubectl create -f kubia-rc.yaml')
            ensure_rc_ready('kubia')
        run('kubectl delete svc kubia', True)

        run('kubectl create -f kubia-svc.yaml')
        run('kubectl get svc kubia')
        pod_name = run("kubectl get pods -l app=kubia -ojsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name)
        clusterIp = run("kubectl get svc kubia -o=jsonpath='{.spec.clusterIP}'", True)
        run(f"kubectl exec {pod_name} -- curl -s http://{clusterIp}")
        pods = set()
        for i in range(10):
            pods.add(run(f"kubectl exec {pod_name} -- curl -s http://{clusterIp}", True))
        self.assertGreater(len(pods), 1)


    def test_session_affinity(self):
        run('kubectl delete svc kubia', True)
        run('kubectl delete svc kubia-session-affinity', True)

        run('kubectl create -f kubia-session-affinity-svc.yaml')
        run('kubectl get svc kubia-session-affinity')
        run('kubectl describe svc kubia-session-affinity')
        pod_name = run("kubectl get pods -l app=kubia -ojsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name)
        clusterIp = run("kubectl get svc kubia -o=jsonpath='{.spec.clusterIP}'", True)
        pods = set()
        for i in range(10):
            pods.add(run(f"kubectl exec {pod_name} -- curl -s http://{clusterIp}", True))
        self.assertEqual(len(pods), 1)

    def test_discovering_service(self):
        run('kubectl delete po -l app=kubia', True)  # in order to regenerate pod

        pod_name = run("kubectl get pods -l app=kubia -ojsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name)
        with self.subTest("Discovering through env"):
            run(f'kubectl exec {pod_name} -- env')
            run(f"kubectl exec {pod_name} -- bash -c 'curl -s http://$KUBIA_SERVICE_HOST:$KUBIA_SERVICE_PORT'")
        with self.subTest("Discovering through DNS"):
            run(f'kubectl exec {pod_name} -- curl -s http://kubia.default.svc.cluster.local')
            run(f'kubectl exec {pod_name} -- curl -s http://kubia.default.svc.cluster.local')
            run(f'kubectl exec {pod_name} -- curl -s http://kubia.default')
            run(f'kubectl exec {pod_name} -- curl -s http://kubia')


    def test_configuring_service_endpoints(self):
        run('kubectl delete svc external-service', True)  # also delete Endpoints associated with the Service

        # Manually configuring service endpoints
        run('kubectl create -f external-service.yaml')
        run('kubectl get svc external-service')
        run('kubectl create -f external-service-endpoints.yaml')
        run('kubectl get ep external-service')

        # If you later decide to migrate the external service to pods running inside Kubernetes,
        # you can add a selector to the service, thereby making its Endpoints managed automatically.
        with self.subTest('Migrating the external service to pods running inside Kubernetes by adding a selector to the service'):
            json_def = json.loads(run('kubectl get svc external-service -o json', True))
            json_def['spec']['ports'][0]['targetPort'] = 8080
            json_def['spec']['selector'] = {'app': 'kubia'}
            with open('/tmp/external-service-with-selector.yaml', 'wb') as fp:
                fp.write(yaml.dump(json_def).encode('utf-8'))
            run("cat /tmp/external-service-with-selector.yaml")
            run(f'kubectl replace -f /tmp/external-service-with-selector.yaml')
            run('kubectl get svc external-service')
            run('kubectl get ep external-service')


        # by removing the selector from a Service, Kubernetes stops updating its Endpoints.
        with self.subTest("Removing the selector from a Service"):
            json_def = json.loads(run('kubectl get svc external-service -o json', True))
            del json_def['spec']['selector']
            with open('/tmp/external-service-remove-selector.yaml', 'wb') as fp:
                fp.write(yaml.dump(json_def).encode('utf-8'))
            run("cat /tmp/external-service-remove-selector.yaml")
            run(f'kubectl replace -f /tmp/external-service-remove-selector.yaml')
            run('kubectl get svc external-service')
            run('kubectl get ep external-service')  # no change to Endpoints


    def test_creating_external_name_service(self):
        run('kubectl delete svc external-service-external-name', True)
        run('kubectl create -f external-service-external-name.yaml')
        # there should be no clusterIp
        run('kubectl get svc external-service-external-name')
        pod_name = run("kubectl get pods -l app=kubia -ojsonpath='{.items[0].metadata.name}'", True)
        ensure_pod_phase(pod_name)
        run(f'kubectl exec {pod_name} -- curl -s -H "Host: www.baidu.com" external-service-external-name')


    def test_exposing_services_to_external_clients(self):
        with self.subTest("Using a NodePort service"):
            run('kubectl delete svc kubia-nodeport', True)

            run('kubectl create -f kubia-svc-nodeport.yaml')
            run('kubectl get svc kubia-nodeport')
            node_port_service = run('minikube service kubia-nodeport --url', True)
            run(f'curl -s {node_port_service}')

        with self.subTest('Exposing a service through an external load balancer'):
            run('kubectl delete svc kubia-loadbalancer', True)
            run('kubectl create -f kubia-svc-loadbalancer.yaml')
            run('kubectl get svc kubia-loadbalancer')