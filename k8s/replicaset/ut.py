#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
import time
import json

class UnitTest(unittest.TestCase):


    def test_create(self):
        '''
        Run this tc first.
        You can run =kubectl delete all --all= beforehand.
        '''
        run('kubectl delete rs kubia', True)
        run('kubectl create -f kubia-replicaset.yaml')
        run('kubectl get rs')
        run('kubectl get pods --show-labels')
