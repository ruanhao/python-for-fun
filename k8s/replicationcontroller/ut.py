#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
import time
import json

class UnitTest(unittest.TestCase):


    def test_create(self):
        '''
        Run this tc first
        '''
        run('kubectl delete rc kubia', True)
        run('kubectl create -f kubia-rc.yaml')
        run('kubectl get rc')
        run('kubectl get pods --show-labels')


    def test_owner_references(self):
        '''
        Although a pod isn’t tied to a ReplicationController, the pod does reference it in the metadata.ownerReferences field,
        which you can use to easily find which ReplicationController a pod belongs to.
        '''
        ret = json.loads(run('kubectl get pod -o json', True))
        for pod in ret['items']:
            metadata = pod['metadata']
            pod_name = metadata['name']
            refs = [(ref['kind'], ref['name']) for ref in metadata['ownerReferences']]
            print(f"{pod_name} => {refs}")

    def test_scale(self):
        # scale up
        run('kubectl scale rc kubia --replicas=10')
        run('kubectl get rc kubia')
        # scale down
        run('kubectl scale rc kubia --replicas=2')
        run('kubectl get rc kubia')


    def test_delete(self):
        '''
        When deleting a ReplicationController with kubectl delete,
        you can keep its pods running by passing the --cascade=false option to the command:

        $ kubectl delete rc kubia --cascade=false
        replicationcontroller "kubia" deleted

        '''
        pass
