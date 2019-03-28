#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from k8s_utils import run
import unittest
import time

class UnitTest(unittest.TestCase):

    def setUp(self):
        run('kubectl delete rc kubia', quiet=True)
        run('kubectl delete svc kubia-http', quiet=True)


    def test_simple_run(self):
        # --port=8080 option tells Kubernetes that your app is listening on port 8080
        # --generator option tells Kubernetes to create a ReplicationController instead of a Deployment
        run('kubectl run kubia --image=luksa/kubia --port=8080 --generator=run/v1')
        run('kubectl get rc -o wide')
        run('kubectl get pods -o wide')

        # create service of type LoadBalancer
        run('kubectl expose rc kubia --type=LoadBalancer --name kubia-http')
        # It doesn’t have an external IP address yet,
        # because it takes time for the load balancer to be created by the cloud infrastructure Kubernetes is running on.
        # Minikube doesn’t support LoadBalancer services
        run('kubectl get svc')

        time.sleep(3)           # wait for pod ready
        url = run('minikube service kubia-http --url')
        run(f'curl -Ss {url}')

        # increase replicas
        run('kubectl scale rc kubia --replicas=3')
        run('kubectl get rc')
        run('kubectl get pods -o wide')
        time.sleep(10)
        run(f'curl -Ss {url}')
        run(f'curl -Ss {url}')
        run(f'curl -Ss {url}')
