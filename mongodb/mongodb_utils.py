#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
format='%(asctime)s - %(name)s - %(levelname)-8s - %(threadName)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import re
import json
import pymongo
import datetime
import time
import uuid
import subprocess
import sys
from pprint import pprint
from pymongo import MongoClient
from bson import json_util
import boto3
from troposphere import Tags, Ref
from troposphere.ec2 import SecurityGroup, SecurityGroupRule, NetworkInterfaceProperty, Instance
from troposphere import Output, Template, Ref, GetAtt

from aws_utils import ts_add_instance_with_public_ip
from aws_utils import ts_add_security_group
from aws_utils import init_cf_env
from aws_utils import dump_template
from aws_utils import cf_client


DOCKER_NETWORK = 'mongo-replica-set'
MONGO_VERSION = '4.1.11'

AMI = 'ami-0c827dd4b5ccc3790'


def run(script, quiet=False, timeout=60, translation=None):
    if quiet is False:
        logger.info(u'\u21a9')
        print(script)
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

def get_rs_client(*hosts, rs='rs0'):
    url = f'mongodb://{",".join(hosts)}/?replicaSet={rs}'
    logger.info(url)
    return MongoClient(url)


def new_collection(db, cname):
    c = db[cname]
    c.drop()
    return c

def timeit(callable):
    begin = time.time()
    callable()
    end = time.time()
    return end - begin


def ts():
    print(datetime.datetime.now())



def random_str(len=5):
    return str(uuid.uuid4()).replace('-', '')[:len]

def key_find(lst, key, value):
    return next((item for item in lst if item[key] == value), None)


def wait_until(func, expect, desc=None, delay=10, tries=10):
    while tries >= 0:
        actual = func()
        logger.debug(f"Waiting until [{actual} => {expect}] ...")
        if actual == expect:
            return
        time.sleep(delay)
        tries -= 1
    raise Exception(f"actual[{actual}] != expected[{expect}] ({desc})")

def create_replica_set(replicas=3):
    run('docker stop `docker ps --format="{{.Names}}" | grep mongo`', True)
    run(f'docker network rm {DOCKER_NETWORK}', True)
    run(f'docker network create {DOCKER_NETWORK}')
    replica_set_name = f'rs{replicas}'
    config = {'_id': replica_set_name, 'members': []}
    for i in range(0, replicas):
        hostname = f'mongo{i}'
        replica_ops = f'--replSet {replica_set_name} --bind_ip localhost,{hostname}'
        mapping_port = 27017 + i
        run(f'docker run --rm -d --network {DOCKER_NETWORK} --hostname {hostname} --name {hostname} -p {mapping_port}:27017 mongo:{MONGO_VERSION} {replica_ops}')
        if i == 0:              # master
            master = MongoClient('localhost', mapping_port)
            master.server_info()  # ensure beging started
            config['members'].append({'_id': i, 'host': f'{hostname}:27017', 'priority': 99})
        else:
            MongoClient('localhost', mapping_port).server_info()  # ensure beging started
            config['members'].append({'_id': i, 'host': f'{hostname}:27017'})
    master.admin.command("replSetInitiate", config)
    # run("""docker exec mongo0 mongo --quiet --eval 'rs.initiate({_id: replica_set_name, members:[{_id: 0, host: "mongo0:27017", priority: 99}, {_id: 1, host: "mongo1:27017"}, {_id: 2, host: "mongo2:27017"}]})'""")
    # wait_until(lambda: run("""mongo --quiet --eval 'rs.status()["members"][0].stateStr'""")[0], 'PRIMARY')
    wait_until(lambda: master.is_primary, True)
    return replica_set_name


def create_replica_set_on_aws(replicas=3):
    test_stack_name = 'TestMongoDbReplSet'
    init_cf_env(test_stack_name)
    ###
    t = Template()
    sg = ts_add_security_group(t)
    for i in range(0, replicas):
        ts_add_instance_with_public_ip(t, Ref(sg), name=f"Mongo{i}", image_id=AMI, tag='mongo')

    t.add_output([Output(f'PublicIp{i}', Value=GetAtt(f"Mongo{i}", "PublicIp")) for i in range(0, replicas)])
    t.add_output([Output(f'PublicDnsName{i}', Value=GetAtt(f"Mongo{i}", "PublicDnsName")) for i in range(0, replicas)])
    t.add_output([Output(f'PrivateIp{i}', Value=GetAtt(f"Mongo{i}", "PrivateIp")) for i in range(0, replicas)])

    dump_template(t, True)
    cf_client.create_stack(
        StackName=test_stack_name,
        TemplateBody=t.to_yaml(),
    )
    cf_client.get_waiter('stack_create_complete').wait(StackName=test_stack_name)
    outputs = cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs']
    time.sleep(10)           # wait for ssh service starting up
    rs_info = {}
    for i in range(0, replicas):
        node = f'mongo{i}'
        public_ip = key_find(outputs, 'OutputKey', f'PublicIp{i}')['OutputValue']
        public_dns = key_find(outputs, 'OutputKey', f'PublicDnsName{i}')['OutputValue']
        private_ip = key_find(outputs, 'OutputKey', f'PrivateIp{i}')['OutputValue']
        rs_info[node] = {'ip': public_ip, 'dns': public_dns, 'private_ip': private_ip}

    config = {
        '_id': 'rs0',
        'members': [{'_id': idx, 'host': info['dns']} for idx, (node, info) in enumerate(rs_info.items())]
    }
    MongoClient(public_ip, 27017).admin.command("replSetInitiate", config)
    logger.info("Replica set on AWS initiated:")
    pprint(rs_info)
    c = get_rs_client(*[info['dns'] for _, info in rs_info.items()])
    wait_until(lambda: c.primary is not None, True)
    logger.info(f'Primary: {c.primary}')
    return c, rs_info


def mock_network_partition(rs_info, target=None, incoming=False, outcoming=False):
    '''
    rs_info = {
      'mongo0': {
        'ip': "xxx",
        'dns': "xxx",
        'private_ip': "xxx",
      }
    }

    target = [ip|private_ip|dns]
    '''
    if target is None:          # default is master
        c = get_rs_client(*[info['dns'] for _, info in rs_info.items()])
        wait_until(lambda: c.primary is not None, True)
        target, _port = c.primary

    target_node = None
    for node, info in rs_info.items():
        if info['ip'] == target or info['private_ip'] == target or info['dns'] == target:
            target_node = node

    assert target_node is not None

    target_node_ip = rs_info[target_node]['ip']

    ips = []
    for node, info in rs_info.items():
        if node != target_node:
            ips.append(info['private_ip'])
            ips.append(info['ip'])
    if incoming is False:
        run(f"ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ec2-user@{target_node_ip} sudo iptables -I INPUT  -s {','.join(ips)} -j DROP")
    if outcoming is False:
        run(f"ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ec2-user@{target_node_ip} sudo iptables -I OUTPUT -d {','.join(ips)} -j DROP")

def mock_network_partition_recovery(rs_info, target=None):
    if target is None:          # default is master
        c = get_rs_client(*[info['dns'] for _, info in rs_info.items()])
        wait_until(lambda: c.primary is not None, True)
        target, _port = c.primary

    target_node = None
    for node, info in rs_info.items():
        if info['ip'] == target or info['private_ip'] == target or info['dns'] == target:
            target_node = node

    assert target_node is not None

    target_node_ip = rs_info[target_node]['ip']
    run(f"ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ec2-user@{target_node_ip} sudo iptables -F") # network recovery
