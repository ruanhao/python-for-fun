#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import boto3
import inspect
import os
from troposphere import Tags, Ref
from troposphere.ec2 import SecurityGroup, SecurityGroupRule, NetworkInterfaceProperty, Instance

ec2_client = boto3.client('ec2')
cf_client = boto3.client('cloudformation')

def get_default_vpc():
    return ec2_client.describe_vpcs(
        Filters=[
            {
                'Name': 'isDefault',
                'Values': ["true"]
            }
        ]
    )['Vpcs'][0]['VpcId']

def get_first_subnet(vpc_id=None):
    if vpc_id is None:
        vpc_id = get_default_vpc()

    return ec2_client.describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }
        ]
    )['Subnets'][0]['SubnetId']


def get_azs(region=None):
    if region is not None:
        client = boto3.client('ec2', region_name=region)
    else:
        client = ec2_client
    azresp = client.describe_availability_zones(Filters=[{'Name':'state','Values':['available']}])
    return [i['ZoneName'] for i in azresp['AvailabilityZones']]


def run(script, quiet=False):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=60)
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if quiet is False:
        print(f'{stdout_str}')
        print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            raise Exception('Exit Code: %s' % proc.returncode)
    return stdout_str


def key_find(lst, key, value):
    return next((item for item in lst if item[key] == value), None)


def dump_template(t, quiet=False, format='yaml'):
    output = getattr(t, f'to_{format}')()
    if quiet is False:
        print(output)
    caller = inspect.stack()[1].function
    with open(f'/tmp/{caller}.{format}', 'w+') as fp:
        fp.write(output)

def init_cf_env(stack_name):
    cf_client.delete_stack(StackName=stack_name)
    cf_client.get_waiter('stack_delete_complete').wait(StackName=stack_name)


def get_ubuntu_image_id():
    response = ec2_client.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': ['ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-????????']
                },
                {
                    'Name': 'state',
                    'Values': ['available']
                }
            ],
            Owners=['099720109477'],
        )
    return sorted(response['Images'], key=lambda img: img.get('CreationDate'))[-1]['ImageId']

def get_linux2_image_id():
    response = ec2_client.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': ['amzn2-ami-hvm-2.0.????????-x86_64-gp2']
                },
                {
                    'Name': 'state',
                    'Values': ['available']
                }
            ],
            Owners=['amazon'],
        )
    return sorted(response['Images'], key=lambda img: img.get('CreationDate'))[-1]['ImageId']


def get_my_key():
    return os.getenv("MY_AWS_KEY", 'cisco-aws-key')


def ts_add_instance_with_public_ip(t,
                                   security_group_ref,
                                   name='MyInstance',
                                   image_id=None,
                                   subnet_id=None,
                                   tag="aws test instance",
                                   public=True):
    if image_id is None:
        image_id = get_linux2_image_id()
    if subnet_id is None:
        subnet_id = get_first_subnet()

    return t.add_resource(Instance(
        name,
        KeyName=get_my_key(),
        InstanceType="m4.xlarge",
        ImageId=image_id,
        NetworkInterfaces=[
            NetworkInterfaceProperty(
                AssociatePublicIpAddress=public,
                DeviceIndex=0,
                DeleteOnTermination=True,
                GroupSet=[security_group_ref],  # associates the security group
                SubnetId=subnet_id
            ),
        ],
        Tags=Tags(
            Name=tag,
            Application=Ref("AWS::StackName"),
            Developer="cisco::haoru",
        ),
    ))



def ts_add_security_group(t, vpc_id=None, name='MySecurityGroup', desc='Enable all ingress'):
    if vpc_id is None:
        vpc_id = get_default_vpc()
    return t.add_resource(SecurityGroup(
        name,
        GroupDescription=desc,
        VpcId=vpc_id,
        SecurityGroupIngress=[
            SecurityGroupRule(
                IpProtocol='tcp',
                CidrIp="0.0.0.0/0",
                FromPort=0,
                ToPort=65535
            ),
        ],
        Tags=Tags(
            Application=Ref("AWS::StackName"),
            Developer="cisco::haoru",
        )
    ))

def get_ec2_client():
    return boto3.client('ec2')

def get_cf_client():
    return boto3.client('cloudformation')

def get_output_value(outputs, key):
    return key_find(outputs, 'OutputKey', key)['OutputValue']
