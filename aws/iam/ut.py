#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import time
import unittest
import boto3
from aws_utils import *
import troposphere.iam
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Sub
from troposphere import Parameter, Ref, Tags, Template
from troposphere.policies import CreationPolicy, ResourceSignal
from troposphere.iam import Role, InstanceProfile
from awacs.aws import Allow, Statement, Principal, Policy, PolicyDocument, Action, StringEquals, Condition
from awacs.sts import AssumeRole
from troposphere.ec2 import (Route,
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

cf_client = get_cf_client()

class UnitTest(unittest.TestCase):

    def test_attaching_role_to_instance(self):
        '''
        The following example will show you how to use an IAM role for an EC2 instance.
        The following snippet shows a one-liner terminating an EC2 instance after 1 minute.
        '''
        test_stack_name = 'TestAttachingRole2Instance'
        init_cf_env(test_stack_name)
        ###

        t = Template()
        security_group = ts_add_security_group(t)
        role = t.add_resource(Role(
            "MyRole",
            AssumeRolePolicyDocument=Policy(  # allow the EC2 service to trust this role
                Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[AssumeRole],
                        Principal=Principal("Service", ["ec2.amazonaws.com"])
                    )
                ]
            ),
            Policies=[
                troposphere.iam.Policy(
                    PolicyName="my_ec2_policy",
                    PolicyDocument=PolicyDocument(
                        Statement=[
                            Statement(
                                Effect=Allow,
                                Action=[
                                    Action("ec2", "StopInstances"),
                                ],
                                Resource=["*"],
                                # only allow if tagged with the stack ID.
                                Condition=Condition(StringEquals({'ec2:ResourceTag/aws:cloudformation:stack-id': Ref('AWS::StackId')})),
                            )
                        ]
                    )
                ),
            ]
        ))
        instance_profile = t.add_resource(InstanceProfile(
            "MyInstanceProfile",
            Roles=[
                Ref(role)
            ]
        ))
        instance = ts_add_instance_with_public_ip(t, Ref(security_group), tag='role-attachment')
        instance.IamInstanceProfile = Ref(instance_profile)
        t.add_output([
            Output(
                "InstanceId",
                Value=Ref(instance)
            ),
            Output(
                "PublicIP",
                Value=GetAtt(instance, "PublicIp"),
            ),
            Output(
                "Region",
                Value=Ref('AWS::Region')
            ),

        ])
        dump_template(t, True)
        cf_client.create_stack(
            StackName=test_stack_name,
            TemplateBody=t.to_yaml(),
            Capabilities=['CAPABILITY_NAMED_IAM'],
        )
        cf_client.get_waiter('stack_create_complete').wait(StackName=test_stack_name)
        time.sleep(10)
        public_ip = key_find(cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs'],
                             'OutputKey', 'PublicIP')['OutputValue']
        instance_id = key_find(cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs'],
                             'OutputKey', 'InstanceId')['OutputValue']
        region = key_find(cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs'],
                             'OutputKey', 'Region')['OutputValue']

        # When using an IAM role, your access keys are injected into your EC2 instance automatically.
        run(f"ssh -o 'StrictHostKeyChecking no' ec2-user@{public_ip} aws ec2 stop-instances --instance-ids {instance_id} --region {region}")