#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import time
import unittest
import boto3
from itertools import chain
from pprint import pprint
from aws_utils import *
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Sub
from troposphere import Parameter, Ref, Tags, Template, Condition, Equals
from troposphere.policies import CreationPolicy, ResourceSignal
from troposphere.autoscaling import LaunchConfiguration, AutoScalingGroup, Tag
from troposphere.efs import FileSystem, MountTarget
from troposphere.ec2 import (Route,
                             EIP,
                             Volume,
                             VolumeAttachment,
                             BlockDeviceMapping,
                             EBSBlockDevice,
                             NatGateway,
                             SubnetRouteTableAssociation,
                             Subnet,
                             RouteTable,
                             VPCGatewayAttachment,
                             VPC,
                             Instance,
                             InternetGateway,
                             SecurityGroup,
                             SecurityGroupRule,
                             NetworkInterfaceProperty)

ec2_client = get_ec2_client()
cf_client = get_cf_client()

KEY = get_my_key()
SSH_OPTIONS = "-o StrictHostKeyChecking=no -o LogLevel=ERROR"

class UnitTest(unittest.TestCase):


    def test_ensuring_an_ec2_instance_is_always_running(self):
        test_stack_name = "TestEnsureOneInstance"
        init_cf_env(test_stack_name)
        ###
        subnet_ids = [get_first_subnet(), get_subnet(index=1)]
        t = Template()
        sg = ts_add_security_group(t)
        launch_config = t.add_resource(LaunchConfiguration(
            "MyLaunchConfiguration",
            ImageId=get_linux2_image_id(),
            InstanceType='t2.micro',
            KeyName=KEY,
            SecurityGroups=[Ref(sg)],
            AssociatePublicIpAddress=True,
            InstanceMonitoring=False,  # Controls whether instances in this group are launched with detailed (true) or basic (false) monitoring
        ))
        auto_scaling_group = t.add_resource(AutoScalingGroup(
            "MyAutoScalingGroup",
            LaunchConfigurationName=Ref(launch_config),
            DesiredCapacity=1,
            MinSize=1,
            MaxSize=1,
            VPCZoneIdentifier=subnet_ids,
            HealthCheckGracePeriod=600,  # The amount of time, in seconds, that Amazon EC2 Auto Scaling waits before
                                         # checking the health status of an EC2 instance that has come into service.
            HealthCheckType='EC2',  # Use internal health chack of EC2 service to discover issues with the vm
            Tags=[
                Tag("Name", test_stack_name, True)  # 'True' means: Attaches the same tags to the virtual machine started by this auto-scaling group
            ]
        ))
        dump_template(t, True)
        create_stack(test_stack_name, t)
        resp = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", 'Values': [test_stack_name]}])
        all_instances = list(chain.from_iterable([reservation['Instances'] for reservation in resp['Reservations']]))
        running_instances = [ins for ins in all_instances if ins['State'] == {'Code': 16, 'Name': 'running'}]
        self.assertEqual(len(running_instances), 1)
        instance = running_instances[0]
        public_ip = instance['PublicIpAddress']
        subnet_id = instance['SubnetId']
        instance_id = instance['InstanceId']
        self.assertIn(subnet_id, subnet_ids)
        run(f'aws ec2 terminate-instances --instance-ids {instance_id}')

        time.sleep(180)         # wait for new instance starting up

        resp = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", 'Values': [test_stack_name]}])
        all_instances = list(chain.from_iterable([reservation['Instances'] for reservation in resp['Reservations']]))
        running_instances = [ins for ins in all_instances if ins['State'] == {'Code': 16, 'Name': 'running'}]
        self.assertEqual(len(running_instances), 1)
        instance = running_instances[0]
        subnet_id = instance['SubnetId']
        self.assertIn(subnet_id, subnet_ids)
        instance_id2 = instance['InstanceId']
        self.assertNotEqual(instance_id2, instance_id)
