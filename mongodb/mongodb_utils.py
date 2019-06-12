#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import pymongo
import time
import uuid
import subprocess
import sys
from pymongo import MongoClient
from bson import json_util

DOCKER_NETWORK = 'mongo-replica-set'
MONGO_VERSION = '4.1.11'


def run(script, quiet=False, timeout=60, translation=None):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=timeout)
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if translation is not None:
        stdout_str = translate(stdout_str, translation)
        stderr_str = translate(stderr_str, translation)
    if quiet is False:
        if stdout_str.strip():
            print(f'{stdout_str}')
        if stderr_str.strip():
            print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            e = Exception(stderr_str)
            e.err_code = proc.returncode
            e.err_msg = stderr_str
            raise e
    return stdout_str, stderr_str


def get_client(host='localhost', port=27017):
    return MongoClient(host, port)

def new_collection(db, cname):
    c = db[cname]
    c.drop()
    return c

def timeit(callable):
    begin = time.time()
    callable()
    end = time.time()
    return end - begin





def random_str(len=5):
    return str(uuid.uuid4()).replace('-', '')[:len]

def key_find(lst, key, value):
    return next((item for item in lst if item[key] == value), None)


def _wait_until(func, expect, desc=None, delay=3, tries=10):
    while tries >= 0:
        actual = func()
        if actual == expect:
            return
        time.sleep(delay)
        tries -= 1
    raise Exception(f"actual[{actual}] != expected[{expected}] ({desc})")

def create_replica_set(replicas=3):
    run('docker stop `docker ps --format="{{.Names}}" | grep mongo`', True)
    run(f'docker network rm {DOCKER_NETWORK}', True)
    run(f'docker network create {DOCKER_NETWORK}')
    for i in range(0, replicas):
        hostname = f'mongo{i}'
        replica_ops = f'--replSet myrs --bind_ip localhost,{hostname}'
        run(f'docker run --privileged --rm -d --network {DOCKER_NETWORK} --hostname {hostname} --name {hostname} -p {27017+i}:27017 mongo:{MONGO_VERSION} {replica_ops}')

    time.sleep(5)               # wait for all mongodbs started
    run("""docker exec mongo0 mongo --quiet --eval 'rs.initiate({_id: "myrs", members:[{_id: 0, host: "mongo0:27017", priority: 99}, {_id: 1, host: "mongo1:27017"}, {_id: 2, host: "mongo2:27017"}]})'""")
    _wait_until(lambda: run("""mongo --quiet --eval 'rs.status()["members"][0].stateStr'""")[0], 'PRIMARY')
