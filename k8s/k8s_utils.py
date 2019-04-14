#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import time
import json


def get_pod_phase(name):
    stdout = run(f'kubectl get pods {name} -o json', True)
    if not stdout:
        return
    stdout_json = json.loads(stdout)
    return stdout_json['status']['phase']

def is_rc_ready(name, ns='default'):
    stdout = run(f'kubectl get rc {name} -o json -n {ns}', True)
    if not stdout:
        return False
    status = json.loads(stdout).get('status')
    ready = status.get('readyReplicas')
    if not ready:
        return False
    return status['replicas'] == ready

def is_deploy_ready(name, ns='default'):
    stdout = run(f'kubectl get deploy {name} -o json -n {ns}', True)
    if not stdout:
        return False
    status = json.loads(stdout).get('status')
    ready = status.get('readyReplicas')
    if not ready:
        return False
    return status['replicas'] == ready






def ensure_rc_ready(name, ns='default', tries=1):
    if tries > 60:
        raise Exception(f"Exceed max tries to ensure rc {name} ready")
    if is_rc_ready(name, ns):
        return
    time.sleep(3)
    ensure_rc_ready(name, ns, tries+1)

def ensure_deploy_ready(name, ns='default', tries=1):
    if tries > 60:
        raise Exception(f"Exceed max tries to ensure rc {name} ready")
    if is_deploy_ready(name, ns):
        return
    time.sleep(3)
    ensure_deploy_ready(name, ns, tries+1)

def ensure_namespace_phase(name, expected_phase='Active', tries=1):
    if tries > 60:
        raise Exception(f"Exceed max tries to ensure namespace {name}'s status ({expected_phase})")
    stdout = run(f'kubectl get ns {name} -o json', True)
    if not stdout:
        if expected_phase == 'Deleted':
            return
    else:
        stdout_json = json.loads(stdout)
        if stdout_json['status']['phase'] == expected_phase:
            return
    time.sleep(3)
    ensure_namespace_phase(name, expected_phase, tries+1)


def ensure_pod_phase(name, expected_phase='Running', ns='default', tries=1):
    if tries > 60:
        raise Exception(f"Exceed max tries to ensure pod {name}'s phase ({expected_phase})")
    stdout = run(f'kubectl get pods {name} -n {ns} -o json', True)
    if not stdout:
        if expected_phase == 'Deleted':
            return
    else:
        stdout_json = json.loads(stdout)
        if stdout_json['status']['phase'] == expected_phase:
            return
    time.sleep(3)
    ensure_pod_phase(name, expected_phase, ns, tries+1)


def run(script, quiet=False):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if quiet is False:
        print(f'{stdout_str}')
        print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            raise Exception('Exit Code: %s' % proc.returncode)
    return stdout_str


def get_ingress_address(name, tries=1):
    while True:
        if tries > 60:
            raise Exception(f"Exceed max tries to get ing {name}'s IP")
        ip_addr = run(f"kubectl get ing {name} -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'", True)
        if ip_addr:
            return ip_addr
        time.sleep(3)
        tries += 1


def init_test_env(ns):
    run(f"kubectl delete ns {ns}", True)
    ensure_namespace_phase(ns, 'Deleted')
    run(f"kubectl create ns {ns}", True)


def ensure_replicas(name, replicas, type_='deploy', ns='default', tries=1):
    stdout = run(f"kubectl get {type_} {name} -n {ns} -o jsonpath='{{.status.replicas}}'", True)
    if stdout and int(stdout) == replicas:
        return
    if tries > 60:
        raise Exception(f"Exceed max tries to ensure {type_} {name}'s replicas: {replicas}")
    time.sleep(10)
    ensure_replicas(name, replicas, type_, ns, tries+1)
