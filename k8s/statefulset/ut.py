#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
import time
import datetime
import subprocess
from contextlib import redirect_stdout
from contextlib import redirect_stderr

def _clear():
    run('kubectl delete all --all', True)
    run('kubectl delete pvc --all', True)
    run('kubectl delete pv --all', True)




class UnitTest(unittest.TestCase):

    def test_create_without_pv_predefined(self):
        _clear()

        run('kubectl create -f kubia-statefulset.yaml')
        ensure_pod_phase('kubia-0', 'Running')
        run('kubectl get sts kubia')
        run('kubectl get po')
        run('kubectl get pvc')
        run('kubectl get pv')
        storage_class = run("""kubectl get pvc -o jsonpath='{.items[?(@.metadata.name=="data-kubia-0")].spec.storageClassName}'""", True)
        self.assertEqual(storage_class, 'standard')
        phase = run("""kubectl get pv -o jsonpath='{.items[?(@.spec.claimRef.name=="data-kubia-0")].status.phase}'""", True)
        self.assertEqual(phase, 'Bound')

    def test_create(self):
        '''
        storageClassName is not set in pvc template, which means using dynamically provisioning pv.
        '''
        _clear()

        run('kubectl create -f persistent-volumes-hostpath.yaml')
        run('kubectl create -f kubia-statefulset.yaml')
        ensure_pod_phase('kubia-0', 'Running')
        run('kubectl get sts kubia')
        run('kubectl get po')
        run('kubectl get pvc')
        run('kubectl get pv')
        storage_class = run("""kubectl get pvc -o jsonpath='{.items[?(@.metadata.name=="data-kubia-0")].spec.storageClassName}'""", True)
        self.assertEqual(storage_class, 'standard')
        phase = run("""kubectl get pv -o jsonpath='{.items[?(@.spec.claimRef.name=="data-kubia-0")].status.phase}'""", True)
        self.assertEqual(phase, 'Bound')

    def test_create_with_empty_sc(self):
        '''
        storageClassName is set to "" in pvc template, which means using pre-provisioned pv.
        '''
        _clear()

        run('kubectl create -f persistent-volumes-hostpath.yaml')
        run('kubectl create -f kubia-statefulset-sc-empty.yaml')
        ensure_pod_phase('kubia-0', 'Running')
        run('kubectl get sts kubia')
        run('kubectl get po')
        run('kubectl get pvc')
        run('kubectl get pv')
        storage_class = run("""kubectl get pvc -o jsonpath='{.items[?(@.metadata.name=="data-kubia-0")].spec.storageClassName}'""", True)
        self.assertTrue(not storage_class)
        volume_name = run("""kubectl get pvc -o jsonpath='{.items[?(@.metadata.name=="data-kubia-0")].spec.volumeName}'""", True)
        self.assertIn(volume_name, ['pv-a', 'pv-b', 'pv-c'])
        phase = run("""kubectl get pv -o jsonpath='{.items[?(@.spec.claimRef.name=="data-kubia-0")].status.phase}'""", True)
        self.assertEqual(phase, 'Bound')


    def test_consistent_state(self):
        now1 = str(datetime.datetime.now())
        time.sleep(1)
        now2 = str(datetime.datetime.now())
        p = subprocess.Popen('kubectl proxy --port=48001', shell=True)
        time.sleep(1)

        run(f'curl -s -X POST -d "{now1}" localhost:48001/api/v1/namespaces/default/pods/kubia-0/proxy/')
        run('curl -s localhost:48001/api/v1/namespaces/default/pods/kubia-0/proxy/')
        run('kubectl delete po kubia-0')
        ensure_pod_phase('kubia-0', 'Running')
        output = run('curl -s localhost:48001/api/v1/namespaces/default/pods/kubia-0/proxy/')
        body = output.split('\n')[1]
        index = body.index(':')
        self.assertEqual(now1, body[index+2:])

        p.terminate()
        p.wait()


    def test_peer_discovery(self):
        run('kubectl delete svc kubia', True)
        # create headless service in order to get individual pod through DNS
        run('kubectl create -f kubia-service-headless.yaml')
        run('kubectl run -it srvlookup --image=tutum/dnsutils --rm --restart=Never -- dig SRV kubia.default.svc.cluster.local')


    def test_delete(self):
        run('kubectl get sts kubia')
        run('kubectl delete sts kubia')
        time.sleep(1)
        run('kubectl get po')
        run('kubectl get pvc')  # not deleted
        run('kubectl get pv')   # not released
        output = run("kubectl get pvc -o jsonpath='{.items[*].metadata.name}'", True)
        for name in output.split():
            if name.startswith('data-kubia'):
                run(f'kubectl delete pvc {name}')
        run('kubectl get pvc')  # deleted (blocked until pod is fully deleted)
        run('kubectl get pv')   # deleted if the pv is dynamically provisioned
