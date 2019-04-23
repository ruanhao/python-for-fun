#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import time
import unittest
import boto3
from aws_utils import *
from troposphere import Base64, FindInMap, GetAtt, Join, Output, Sub
from troposphere import Parameter, Ref, Tags, Template
from troposphere.policies import CreationPolicy, ResourceSignal
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

ec2_client = boto3.client('ec2')
cf_client = boto3.client('cloudformation')

KEY = get_my_key()

class UnitTest(unittest.TestCase):


    def test_find_ami(self):
        # Find the current Amazon Linux 2 AMI
        linux2_ami_id = run("aws ec2 describe-images --owners amazon --filters 'Name=name,Values=amzn2-ami-hvm-2.0.????????-x86_64-gp2' 'Name=state,Values=available' --output json | jq -r '.Images | sort_by(.CreationDate) | last(.[]).ImageId'")
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
        self.assertEqual(sorted(response['Images'], key=lambda img: img.get('CreationDate'))[-1]['ImageId'], linux2_ami_id)

        # Find the current Ubuntu Server 16.04 LTS AMI
        run("aws ec2 describe-images --owners 099720109477 --filters 'Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-????????' 'Name=state,Values=available' --output json | jq -r '.Images | sort_by(.CreationDate) | last(.[]).ImageId'")

        # Find the current Red Hat Enterprise Linux 7.5 AMI
        run("aws ec2 describe-images --owners 309956199498 --filters 'Name=name,Values=RHEL-7.5_HVM_GA*' 'Name=state,Values=available' --output json | jq -r '.Images | sort_by(.CreationDate) | last(.[]).ImageId'")


    def test_creating_all_in_one(self):
        '''
        Create VPC, Subnets, IGW, Route, SecurityGroup, Instance at once.
        '''
        test_stack_name = 'TestStack'
        cf_client.delete_stack(StackName=test_stack_name)
        cf_client.get_waiter('stack_delete_complete').wait(StackName=test_stack_name)

        ###

        t = Template()

        keyname_param = t.add_parameter(Parameter(
            "KeyName",
            Description="Name of an existing EC2 KeyPair to enable SSH "
            "access to the instance",
            Type="String",
        ))

        t.add_mapping('RegionMap', {
            "us-east-1":      {"AMI": "ami-7f418316"},
            "us-east-2":      {"AMI": "ami-0c55b159cbfafe1f0"},
            "us-west-1":      {"AMI": "ami-951945d0"},
            "us-west-2":      {"AMI": "ami-16fd7026"},
            "eu-west-1":      {"AMI": "ami-24506250"},
            "sa-east-1":      {"AMI": "ami-3e3be423"},
            "ap-southeast-1": {"AMI": "ami-74dda626"},
            "ap-northeast-1": {"AMI": "ami-dcfa4edd"}
        })

        t.add_resource(VPC(
            "VPC",
            EnableDnsSupport="true",
            CidrBlock="10.100.0.0/16",
            EnableDnsHostnames="true",
            Tags=Tags(
                Application=Ref("AWS::StackName"),
                Developer="cisco::haoru",
            )
        ))

        t.add_resource(InternetGateway(
            "InternetGateway",
            Tags=Tags(
                Application=Ref("AWS::StackName"),
                Developer="cisco::haoru",
            )
        ))

        t.add_resource(VPCGatewayAttachment(
            "IGWAttachment",
            VpcId=Ref("VPC"),
            InternetGatewayId=Ref("InternetGateway"),
        ))

        t.add_resource(RouteTable(
            "RouteTable",
            VpcId=Ref("VPC"),
            Tags=Tags(
                Application=Ref("AWS::StackName"),
                Developer="cisco::haoru",
            )
        ))

        t.add_resource(Route(
            "IGWRoute",
            DependsOn='IGWAttachment',
            GatewayId=Ref("InternetGateway"),
            DestinationCidrBlock="0.0.0.0/0",
            RouteTableId=Ref("RouteTable"),
        ))


        # loop through usable availability zones for the aws account and create a subnet for each zone
        for i, az in list(enumerate(get_azs(), start=1)):
            t.add_resource(Subnet(
                "PublicSubnet{0}".format(i),
                VpcId=Ref("VPC"),
                CidrBlock="10.100.{0}.0/24".format(i),
                AvailabilityZone="{0}".format(az),
                MapPublicIpOnLaunch=True,
                Tags=Tags(
                    Application=Ref("AWS::StackName"),
                    Developer="cisco::haoru",
                )
            ))
            t.add_resource(SubnetRouteTableAssociation(
                "SubnetRouteTableAssociation{0}".format(i),
                SubnetId=Ref("PublicSubnet{0}".format(i)),
                RouteTableId=Ref("RouteTable"),
            ))

        t.add_resource(SecurityGroup(
            "SecurityGroup",
            GroupDescription="Enable all ingress",
            VpcId=Ref('VPC'),
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

        ec2_instance = t.add_resource(Instance(
            "Instance",
            SecurityGroupIds=[Ref('SecurityGroup')],
            SubnetId=Ref('PublicSubnet1'),
            KeyName=Ref(keyname_param),
            InstanceType="m4.xlarge",
            ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
            Tags=Tags(
                Name="aws test troposphere",
                Application=Ref("AWS::StackName"),
                Developer="cisco::haoru",
            ),
            # UserData=Base64(Ref(webport_param)),
        ))

        t.add_output([
            Output(
                "InstanceId",
                Description="InstanceId of the newly created EC2 instance",
                Value=Ref(ec2_instance),
            ),
            Output(
                "AZ",
                Description="Availability Zone of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "AvailabilityZone"),
            ),
            Output(
                "PublicIP",
                Description="Public IP address of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PublicIp"),
            ),
            Output(
                "PrivateIP",
                Description="Private IP address of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PrivateIp"),
            ),
            Output(
                "PublicDNS",
                Description="Public DNSName of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PublicDnsName"),
            ),
            Output(
                "PrivateDNS",
                Description="Private DNSName of the newly created EC2 instance",
                Value=GetAtt(ec2_instance, "PrivateDnsName"),
            ),
        ])
        dump_template(t, True)

        cf_client.create_stack(
            StackName=test_stack_name,
            TemplateBody=t.to_yaml(),
            Parameters=[
                {
                    'ParameterKey': 'KeyName',
                    'ParameterValue': KEY  # Change this value as you wish
                }
            ]
        )
        cf_client.get_waiter('stack_create_complete').wait(StackName=test_stack_name)
        public_ip = key_find(cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs'],
                             'OutputKey', 'PublicIP')['OutputValue']
        time.sleep(5)
        run(f"ssh -o 'StrictHostKeyChecking no' ubuntu@{public_ip} curl -s ifconfig.me")  # run ssh-add <KEY> beforehand


    def test_running_script_on_startup_using_user_data(self):
        test_stack_name = 'TestRunningUserData'
        init_cf_env(test_stack_name)
        ###

        now = str(datetime.datetime.now())

        t = Template()
        security_group = t.add_resource(SecurityGroup(
            "SecurityGroup",
            GroupDescription="Enable all ingress",
            VpcId=get_default_vpc(),
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
        instance = t.add_resource(Instance(
            "MyInstance",
            KeyName=KEY,
            InstanceType="m4.xlarge",
            ImageId=get_linux2_image_id(),  # linux2 has /opt/aws/bin/cfn-signal preinstalled
            NetworkInterfaces=[
                NetworkInterfaceProperty(
                    AssociatePublicIpAddress=True,
                    DeviceIndex=0,
                    GroupSet=[Ref(security_group)],
                    SubnetId=get_first_subnet()
                ),
            ],
            UserData=Base64(Join('', [
                '#!/bin/bash -xe\n',  # user data that begins with shebang will be executed
                f'echo "{now}" > /tmp/now\n',
                '/opt/aws/bin/cfn-signal -e $? ',  # send signal to let cloud formation know it is ready
                '                --stack ', Ref("AWS::StackName"),
                '                --resource MyInstance ',
                '                --region ', Ref("AWS::Region"), '\n'
            ])),
            CreationPolicy=CreationPolicy(
                ResourceSignal=ResourceSignal(Timeout='PT10M')  # expect to receive signal in 10 mins
            ),
            Tags=Tags(
                Name="aws test user data",
                Application=Ref("AWS::StackName"),
                Developer="cisco::haoru",
            ),
        ))
        t.add_output([
            Output(
                "InstanceId",
                Description="InstanceId of the newly created EC2 instance",
                Value=Ref(instance),
            ),
            Output(
                "PublicIP",
                Description="Public IP address of the newly created EC2 instance",
                Value=GetAtt(instance, "PublicIp"),
            ),
        ])
        dump_template(t, True)
        cf_client.create_stack(
            StackName=test_stack_name,
            TemplateBody=t.to_yaml()
        )
        cf_client.get_waiter('stack_create_complete').wait(StackName=test_stack_name)
        public_ip = key_find(cf_client.describe_stacks(StackName=test_stack_name)['Stacks'][0]['Outputs'],
                             'OutputKey', 'PublicIP')['OutputValue']
        actual = run(f"ssh -o 'StrictHostKeyChecking no' ec2-user@{public_ip} cat /tmp/now")
        self.assertEqual(actual, now)
