#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from k8s_utils import run
import json

class UnitTest(unittest.TestCase):


    def test_create(self):
        run('kubectl delete job batch-job', True)

        run('kubectl create -f batch-job.yaml')
        run('kubectl get po')
        run('kubectl get job')


    def test_running_multiple_pod_instances_in_a_job(self):

        with self.subTest("Running job pods sequentially"):
            # This Job will run five pods one after the other.
            # It initially creates one pod, and when the pod's container finishes, it creates the second pod, and so on,
            # until five pods complete successfully.
            # If one of the pods fails, the Job creates a new pod, so the Job may create more than five pods overall.
            run('kubectl delete job multi-completion-batch-job', True)
            run('kubectl create -f multi-completion-batch-job.yaml')
            run('kubectl get job')
            run('kubectl get pod')

        with self.subTest('Running job pods in parallel'):
            # You specify how many pods are allowed to run in parallel with the 'parallelism' Job spec property
            run('kubectl delete job multi-completion-parallel-batch-job', True)
            run('kubectl create -f multi-completion-parallel-batch-job.yaml')
            run('kubectl get job')
            run('kubectl get pod')
            run('kubectl scale job multi-completion-parallel-batch-job --replicas 3')
            run('kubectl get pod')


    def test_time_limited_job(self):
        run('kubectl delete job time-limited-batch-job', True)
        run('kubectl create -f time-limited-batch-job.yaml')
        run('kubectl get job time-limited-batch-job')


    def test_cron_job(self):
        run('kubectl delete cj batch-job-every-fifteen-minutes', True)
        run('kubectl create -f cronjob.yaml')
        run('kubectl get cj')
