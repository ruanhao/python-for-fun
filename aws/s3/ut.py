#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import unittest
from aws_utils import *
import uuid
import json
from pprint import pprint


s3_client = get_s3_client()

class UnitTest(unittest.TestCase):

    def test_s3_cli(self):
        run('rm -rf /tmp/test_s3', True)
        run('rm -rf /tmp/test_s3_bak', True)
        bucket = str(uuid.uuid4())
        ###
        run("mkdir /tmp/test_s3")
        run('for i in {1..3}; do echo $i > /tmp/test_s3/$i; done')
        run(f'aws s3 mb s3://{bucket}')
        run(f'aws s3 sync /tmp/test_s3 s3://{bucket}/backup')
        run(f'aws s3 ls --recursive s3://{bucket}/backup')
        run(f'aws s3 cp --recursive s3://{bucket}/backup /tmp/test_s3_bak')
        run('ls /tmp/test_s3_bak')
        run(f'aws s3 rb --force s3://{bucket}')


    def test_making_object_public(self):
        bucket = str(uuid.uuid4())
        obj_key = str(uuid.uuid4())
        content = run('fortune')
        current_region = run('aws configure get region', True)
        s3_client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={
                'LocationConstraint': current_region
            },
        )
        s3_client.put_object(
            ACL='public-read',  # Allows everybody to read
            Body=content.encode('utf-8'),
            Bucket=bucket,
            Key=obj_key,
            ContentLength=len(content),
            ContentType='text/plain',
        )
        response = s3_client.list_objects(Bucket=bucket)
        self.assertEqual(key_find(response['Contents'], 'Key', obj_key)['Size'], len(content))
        # if you create an S3 bucket in VIRGINIA, public url is like:
        # https://s3.amazonaws.com/bucket-name/file-name
        # if you create the bucket in any other region, url is like:
        # https://s3-conutry-region-number.amazonaws.com/bucket-name/file-name
        public_url = f'https://s3-{current_region}.amazonaws.com/{bucket}/{obj_key}'
        text = run(f'curl -s {public_url}')
        self.assertEqual(text, content)


    def test_web_hosting(self):
        '''
        A bucket policy helps you control access to bucket objects GLOBALLY.
        '''

        bucket = str(uuid.uuid4())
        current_region = run('aws configure get region', True)
        s3_client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={
                'LocationConstraint': current_region
            },
        )
        run(f'aws s3 cp helloworld.html s3://{bucket}/')
        policy = {
            'Version': "2012-10-17",
            'Statement': {
                'Sid': "AddPerm",
                'Effect': "Allow",  # Allows access
                'Principal': "*",    # For everyone
                'Action': ['s3:GetObject'],
                'Resource': [f'arn:aws:s3:::{bucket}/*']
            }
        }
        s3_client.put_bucket_policy(
            Bucket=bucket,
            Policy=json.dumps(policy)
        )
        run(f'aws s3 website s3://{bucket} --index-document helloworld.html')
        run(f'curl -s http://{bucket}.s3-website.{current_region}.amazonaws.com')
