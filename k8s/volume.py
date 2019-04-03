#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
from k8s_utils import ensure_pod_phase
import time
import json
import datetime
import subprocess

class UnitTest(unittest.TestCase):

    def test_empty_dir_vol(self):
        run('kubectl delete pod fortune', True)
        ensure_pod_phase('fortune', 'Deleted')

        run('kubectl create -f fortune-pod.yaml')
        ensure_pod_phase('fortune', 'Running')

        p = subprocess.Popen('kubectl port-forward fortune 8888:80', shell=True)
        time.sleep(1)
        run('curl -s http://localhost:8888')
        p.terminate()

    def test_host_path_vol(self):
        run('kubectl delete pod mongodb', True)
        ensure_pod_phase('mongodb', 'Deleted')

        run('kubectl create -f mongodb-pod-hostpath.yaml')
        ensure_pod_phase('mongodb', 'Running')

        now = str(datetime.datetime.now())
        run(f"""kubectl exec mongodb -- mongo --quiet localhost/mystore --eval 'db.foo.insert({{time: "{now}"}})'""")

        run('kubectl delete pod mongodb', True)
        ensure_pod_phase('mongodb', 'Deleted')

        run('kubectl create -f mongodb-pod-hostpath.yaml')
        ensure_pod_phase('mongodb', 'Running')

        ret = run("""kubectl exec mongodb -- mongo localhost/mystore --quiet --eval 'db.foo.find({}, {_id: 0}).sort({time: -1}).limit(1)'""")
        self.assertEqual(now, json.loads(ret)['time'])

    def test_pv_vol(self):
        # run test_host_path_vol first to inflate data to MongoDB
        run('kubectl delete pvc mongodb-pvc', True)
        run('kubectl delete pv mongodb-pv', True)
        run('kubectl delete pod mongodb', True)
        ensure_pod_phase('mongodb', 'Deleted')

        # create pv first
        run('kubectl create -f mongodb-pv-hostpath.yaml')
        run('kubectl get pv')

        # then create pvc
        run('kubectl create -f mongodb-pvc.yaml')
        run('kubectl get pvc')

        # then create pod using pvc
        run('kubectl create -f mongodb-pod-pvc.yaml')
        ensure_pod_phase('mongodb', 'Running')

        run("""kubectl exec mongodb -- mongo localhost/mystore --quiet --eval 'db.foo.find({})'""")


    def test_dp_pv_vol(self):
        '''
        Dynamical Provision
        '''
        run('kubectl delete pod mongodb', True)
        ensure_pod_phase('mongodb', 'Deleted')
        run('kubectl delete pvc mongodb-pvc', True)
        run('kubectl delete sc fast', True)

        # 1, Define StroageClass
        run('kubectl create -f storageclass-fast-hostpath.yaml')
        run('kubectl get sc')

        # 2, Requesting the storage class in a PersistentVolumeClaim
        run('kubectl create -f mongodb-pvc-dp.yaml')
        run('kubectl get pvc mongodb-pvc')
        run('kubectl get pv')  # Its reclaim policy is Delete, which means the PersistentVolume will be deleted when the PVC is deleted.

        # 3, Create pod using pvc
        run('kubectl create -f mongodb-pod-pvc.yaml')
        ensure_pod_phase('mongodb', 'Running')

        # 4, Verify
        now = str(datetime.datetime.now())
        run(f"""kubectl exec mongodb -- mongo --quiet localhost/mystore --eval 'db.foo.insert({{time: "{now}"}})'""")
        run('kubectl delete pod mongodb')
        ensure_pod_phase('mongodb', 'Deleted')
        run('kubectl create -f mongodb-pod-pvc.yaml')
        ensure_pod_phase('mongodb', 'Running')
        ret = run("""kubectl exec mongodb -- mongo localhost/mystore --quiet --eval 'db.foo.find({}, {_id: 0}).sort({time: -1}).limit(1)'""")
        self.assertEqual(now, json.loads(ret)['time'])
