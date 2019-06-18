#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
format='%(asctime)s - %(name)s - %(levelname)-8s - %(threadName)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

import threading
import random
import unittest
import datetime
import time
import warnings
import pymongo
from pprint import pprint
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.read_preferences import Primary
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

        logger.info(f'host and port current connected to: {c.testdb.client.address}')
        primary, _ = c.primary
        self.assertEqual(primary, c.testdb.client.address[0])
        run(f'ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR ec2-user@{primary} sudo iptables -I INPUT -p tcp --dport 27017 -j DROP')
        with self.assertRaises(pymongo.errors.AutoReconnect):
            # This means that the driver was not able to connect to the old primary,
            # it will attempt to automatically reconnect on subsequent operations.
            c.testdb.testcol.find_one()
        logger.info(f"New primary: {c.primary}")  # can be None now
        # Eventually, the replica set will failover and elect a new primary (this should take no more than a couple of seconds in general).
        # At that point the driver will connect to the new primary and the operation will succeed.
        wait_until(lambda: c.primary is not None, True)
        logger.info(f"New primary: {c.primary}")
        c.testdb.testcol.find_one()  # ok again





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



    def test_read_concern(self):
        with self.subTest("linearizable"):
            '''
            The query may wait for concurrently executing writes to
            propagate to a majority of replica set members before returning results.

            Combined with "majority" write concern, "linearizable" read concern enables multiple threads to
            perform reads and writes on a single document
            as if a single thread performed these operations in real time;
            that is, the corresponding schedule for these reads and writes is considered linearizable.
            '''
            ts = datetime.datetime.now().timestamp()
            rs_client, rs_info = create_replica_set_on_aws()
            self.assertIsInstance(rs_client.read_preference, Primary)  # You can specify linearizable read concern for read operations on the primary ONLY.
            orig_primary, _ = rs_client.primary

            testcol = rs_client.testdb.get_collection('testcol',
                                                      write_concern=WriteConcern(w='majority', wtimeout=5000, j=True),
                                                      read_concern=ReadConcern('linearizable'))

            testcol.insert_one({'a': 123})  # without this, there will be excption below, don't know why ...
            mock_network_partition(rs_info, incoming=True)  # allow incoming traffic here is in order to make stale primary think it is still primary for longer time
            def worker():
                nonlocal testcol
                with self.assertRaises(pymongo.errors.WTimeoutError):
                    testcol.insert_one({'a': ts})

            threading.Thread(target=worker).start()
            time.sleep(0.5)

            # Linearizable read concern guarantees ONLY apply if read operations specify a query filter
            # that uniquely identifies a single document.
            testcol.find({}, max_time_ms=5000)  # max_time_ms not in effect
            with self.assertRaises(pymongo.errors.ExecutionTimeout):
                testcol.find_one({'a': ts}, max_time_ms=5000)

            c = get_client(orig_primary)
            # you can see difference between different levels below
            self.assertIsNone(c.testdb.get_collection('testcol', read_concern=ReadConcern('majority')).find_one({'a': ts}))
            self.assertEqual(c.testdb.get_collection('testcol', read_concern=ReadConcern('local')).find_one({'a': ts})['a'], ts)
            self.assertTrue(c.is_primary)  # make sure it is still writable
            wait_until(lambda: c.is_primary, False)  # it will step down eventually

        with self.subTest("majority"):
            rs_client, rs_info = create_replica_set_on_aws()
            rs_client.testdb.testcol.insert_one({'a': 1})
            mock_network_partition(rs_info)
            rs_client.testdb.testcol.insert_one({'a': 2})
            testcol2 = rs_client.testdb.get_collection('testcol', read_concern=ReadConcern('majority'))
            self.assertEqual(testcol2.count_documents({}), 1)
            time.sleep(30)
            mock_network_partition_recovery(rs_info)
            time.sleep(30)
            self.assertEqual(rs_client.testdb.testcol.count_documents({}), 1)  # rollbacked
            self.assertEqual(rs_client.testdb.testcol.find_one()['a'], 1)


        with self.subTest("local"):
            rs_client, rs_info = create_replica_set_on_aws()
            mock_network_partition(rs_info)
            rs_client.testdb.testcol.insert_one({'a': 1})
            self.assertEqual(rs_client.testdb.testcol.count_documents({}), 1)
            time.sleep(30)
            mock_network_partition_recovery(rs_info)
            time.sleep(30)
            self.assertEqual(rs_client.testdb.testcol.count_documents({}), 0)  # rollbacked


if __name__ == '__main__':
    unittest.main(verbosity=2)