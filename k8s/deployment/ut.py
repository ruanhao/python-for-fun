#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# minikube start
# kubectl run hello-minikube --image=k8s.gcr.io/echoserver:1.10 --port=8080
# kubectl expose deployment hello-minikube --type=NodePort

import unittest
import yaml
import time
import subprocess
import os
from contextlib import redirect_stdout
from contextlib import redirect_stderr
from k8s_utils import run



def _remove_none(obj):
  if isinstance(obj, (list, tuple, set)):
    return type(obj)(_remove_none(x) for x in obj if x is not None)
  elif isinstance(obj, dict):
    return type(obj)((_remove_none(k), _remove_none(v))
      for k, v in obj.items() if k is not None and v is not None)
  else:
    return obj

def _print_yaml(obj):
  yaml_def = yaml.dump(_remove_none(obj.to_dict()), default_flow_style=False)
  print(yaml_def)



class UnitTest(unittest.TestCase):

    def test_create(self):
        '''v1'''
        run('kubectl delete deploy kubia', True)
        run('kubectl delete svc kubia-nodeport', True)

        run('kubectl create -f kubia-deployment-v1.yaml --record')
        run('kubectl get deploy')
        run('kubectl rollout status deployment kubia')  # used specifically for checking a Deployment's status
        run('kubectl get rs')
        run('kubectl get po')
        run('kubectl create -f kubia-svc-nodeport.yaml')


    def test_update(self):
        '''v1 => v2'''
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_create()
        # slow down the update process a little,
        # so you can see that the update is indeed performed in a rolling fashion.
        run("""kubectl patch deployment kubia -p '{"spec": {"minReadySeconds": 10}}'""", True)
        url = run('minikube service kubia-nodeport --url', True)
        p = subprocess.Popen(f'rm -rf /tmp/update.log && while true; do echo "`date +%T` - `curl -s {url}`" >> /tmp/update.log; sleep 1 ; done', shell=True)

        run('kubectl set image deployment kubia nodejs=luksa/kubia:v2 --record')
        run('kubectl rollout status deployment kubia')
        run('echo "=== rollout successfully ===" >> /tmp/update.log', True)
        time.sleep(5)           # check all requests should hit v2
        p.terminate()
        p.wait()
        run("cat /tmp/update.log")
        run('kubectl get rs')   # old ReplicaSet is still there

    def test_rolling_back(self):
        '''
        v2 => v3
        In version 3, you'll introduce a bug that makes your app handle only the first four requests properly.
        All requests from the fifth request onward will return an internal server error (HTTP status code 500).
        '''
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_update()  # ensure current version is v2

        url = run('minikube service kubia-nodeport --url', True)
        p = subprocess.Popen(f'rm -rf /tmp/rollback.log && while true; do echo "`date +%T` - `curl -s {url}`" >> /tmp/rollback.log; sleep 1 ; done',
                             shell=True)
        run('kubectl set image deployment kubia nodejs=luksa/kubia:v3 --record')
        run('kubectl rollout status deployment kubia')
        run('echo "=== rollout to v3 successfully ===" >> /tmp/rollback.log', True)
        time.sleep(5)           # wait for error log of the app
        run('kubectl rollout history deployment kubia')  # revision history
        run('kubectl rollout undo deployment kubia')  # roll back
        run('kubectl rollout status deployment kubia')
        run('echo "=== roll back to v2 successfully ===" >> /tmp/rollback.log', True)
        time.sleep(3)
        p.terminate()
        p.wait()
        run("cat /tmp/rollback.log")
        run('kubectl rollout history deployment kubia')  # revision history
        #  if you want to roll back to the first version, you'd execute the following command:
        #  $ kubectl rollout undo deployment kubia --to-revision=1


    def test_pausing_rolling_out(self):
        '''
        v1 => v4 => v2
        '''
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f), redirect_stderr(f):
                self.test_create()  # v1

        # set version to v4
        run('kubectl set image deployment kubia nodejs=luksa/kubia:v4 --record')
        run("kubectl get deploy/kubia -o jsonpath='{.spec.template.spec.containers[0].image}'")
        run('kubectl rollout pause deployment kubia')
        # modify version to v2
        run('kubectl set image deployment kubia nodejs=luksa/kubia:v2 --record')
        run('kubectl rollout resume deployment kubia')
        run('kubectl rollout status deployment kubia')
        run('kubectl rollout history deployment kubia')  # revision history
        run("kubectl get deploy/kubia -o jsonpath='{.spec.template.spec.containers[0].image}'")
