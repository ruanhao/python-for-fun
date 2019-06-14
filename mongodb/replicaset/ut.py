#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import unittest
import datetime
import time
import warnings
import pymongo
from pprint import pprint
from mongodb_utils import *

SSH_OPTIONS = "-o StrictHostKeyChecking=no -o LogLevel=ERROR"

class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="subprocess.*")


    def test_creating_replica_set(self):
        create_replica_set()


    def test_creating_replica_set_on_aws(self):
        c, rs_info = create_replica_set_on_aws()
        ts = datetime.datetime.now().timestamp()
        c.testdb.testcol.insert({"a": 1, 'ts': ts})
        d = c.testdb.testcol.find_one({'a': 1})
        self.assertEqual(d['ts'], ts)


    def test_network_partition(self):
        c, rs_info = create_replica_set_on_aws()
        c.testdb.testcol.insert_one({'a': 1})
        orig_primary_dns, _ = c.primary
        print(f'Origin primary dns: {orig_primary_dns}')
        secondary_private_ips = []
        secondary_public_ips = []
        for node, info in rs_info.items():
            if info['dns'] == orig_primary_dns:
                orig_primary_ip = info['ip']
            else:
                secondary_private_ips.append(info['private_ip'])
                secondary_public_ips.append(info['ip'])

        print(f'Origin primary ip: {orig_primary_ip}')

        # mock network partition
        for secondary_private_ip in secondary_private_ips:
            run(f"ssh {SSH_OPTIONS} ec2-user@{orig_primary_ip} sudo iptables -I INPUT  -s {secondary_private_ip} -j DROP")
            run(f"ssh {SSH_OPTIONS} ec2-user@{orig_primary_ip} sudo iptables -I OUTPUT  -d {secondary_private_ip} -j DROP")

        for secondary_public_ip in secondary_public_ips:
            run(f"ssh {SSH_OPTIONS} ec2-user@{orig_primary_ip} sudo iptables -I INPUT  -s {secondary_public_ip} -j DROP")
            run(f"ssh {SSH_OPTIONS} ec2-user@{orig_primary_ip} sudo iptables -I OUTPUT  -d {secondary_public_ip} -j DROP")

        time.sleep(30)          # at least 10
        print(f"Current nodes: {c.nodes}")
        wait_until(lambda: c.primary is not None, True)
        new_primary_dns, _ = c.primary
        print(f'New primary dns: {new_primary_dns}')

        self.assertNotEqual(orig_primary_dns, new_primary_dns)  # primary has changed
        orig_primary_member = key_find(c.admin.command('replSetGetStatus')['members'],
                                       'name',
                                       f'{orig_primary_dns}:27017')
        self.assertEqual(orig_primary_member['stateStr'], '(not reachable/healthy)')  # origin primary is not reachable

        client_using_orig_primary = get_client(orig_primary_ip)
        self.assertFalse(client_using_orig_primary.is_primary)  # not writable
        with self.assertRaises(pymongo.mongo_client.NotMasterError):
            client_using_orig_primary.testdb.testcol.insert_one({'a': 2})
        self.assertEqual(client_using_orig_primary.testdb.testcol.count_documents({}), 1)  # readable

        self.assertTrue(c.is_primary)                             # writable
        c.testdb.testcol.insert({'a': 2})

        run(f"ssh {SSH_OPTIONS} ec2-user@{orig_primary_ip} sudo iptables -F")  # network recovery
        time.sleep(30)
        orig_primary_member_after_recovery = key_find(c.admin.command('replSetGetStatus')['members'],
                                       'name',
                                       f'{orig_primary_dns}:27017')
        self.assertEqual(orig_primary_member_after_recovery['stateStr'], 'SECONDARY')  # origin primary is now secondary
        self.assertEqual(client_using_orig_primary.testdb.testcol.count_documents({}), 2)  # data synchronised





if __name__ == '__main__':
    unittest.main(verbosity=2)