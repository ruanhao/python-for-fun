#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
from itertools import groupby
master1 = redis.Redis(host='localhost', port=46379, db=0)


def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'


class UnitTest(unittest.TestCase):

    '''
    {'192.168.33.11:6379@16379': {
        'node_id': '51c5dec8c4c9c66fba6fbc8ad0ae737eead832e7',
        'flags': 'myself,master',
        'master_id': '-',
        'last_ping_sent': '0',
        'last_pong_rcvd': '1607332478000',
        'epoch': '4',
        'slots': [],
        'connected': True
    }},
    ...
    '''
    def test_AFTER_MEET(self):
        nodes = master1.cluster("nodes")
        for node in nodes.values():
            self.assertTrue(node['connected'])

        info = master1.cluster("info")
        '''
        {
            'cluster_state': 'fail',
            'cluster_slots_assigned': '0',
            'cluster_slots_ok': '0',
            'cluster_slots_pfail': '0',
            'cluster_slots_fail': '0',
            'cluster_known_nodes': '6',
            'cluster_size': '0',
            'cluster_current_epoch': '5',
            'cluster_my_epoch': '4',
            'cluster_stats_messages_ping_sent': '911',
            'cluster_stats_messages_pong_sent': '993',
            'cluster_stats_messages_meet_sent': '5',
            'cluster_stats_messages_sent': '1909',
            'cluster_stats_messages_ping_received': '993',
            'cluster_stats_messages_pong_received': '916',
            'cluster_stats_messages_received': '1909'
        }
        '''
        self.assertEqual("6", info['cluster_known_nodes'])


    def test_AFTER_ADDSLOTS(self):
        info = master1.cluster("info")
        self.assertEqual("16384", info['cluster_slots_assigned'])
        self.assertEqual("ok", info['cluster_state'])


    def test_AFTER_REPLICATE(self):
        nodes = master1.cluster("nodes")
        master_nodes = []
        slave_nodes = []
        for node in nodes.values():
            if 'master' in node['flags']:
                master_nodes.append(node)
            if 'slave' in node['flags']:
                slave_nodes.append(node)
        self.assertEqual(3, len(master_nodes))
        self.assertEqual(3, len(slave_nodes))


    def test_AFTER_ONE_MASTER_ADDED(self):
        nodes = master1.cluster("nodes")
        master_nodes = []
        slave_nodes = []
        for node in nodes.values():
            if 'master' in node['flags']:
                master_nodes.append(node)
            if 'slave' in node['flags']:
                slave_nodes.append(node)
        self.assertEqual(4, len(master_nodes))
        self.assertEqual(3, len(slave_nodes))
        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid')
        slotsInfo = master4.cluster('slots')
        slotOfMaster4 = next((slot for slot in slotsInfo if slot[2][2] == master4Id), None)
        self.assertIsNone(slotOfMaster4)


    def test_AFTER_ONE_SLAVE_ADDED(self):
        nodes = master1.cluster("nodes")
        master_nodes = []
        slave_nodes = []
        for node in nodes.values():
            if 'master' in node['flags']:
                master_nodes.append(node)
            if 'slave' in node['flags']:
                slave_nodes.append(node)
        self.assertEqual(4, len(master_nodes))
        self.assertEqual(4, len(slave_nodes))

        master4 = redis.Redis(host='localhost', port=46382)
        slave4 = redis.Redis(host='localhost', port=46392)
        master4Id = master4.cluster('myid').decode()
        slave4Id = slave4.cluster('myid').decode()
        output = master1.cluster('replicas', master4Id)[0].decode()
        self.assertTrue(output.startswith(slave4Id))

    def test_AFTER_RESHARD(self):
        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid')
        slotsInfo = master4.cluster('slots')
        slotOfMaster4 = next((slot for slot in slotsInfo if slot[2][2] == master4Id), None)
        self.assertIsNotNone(slotOfMaster4)
        self.assertEqual(0, slotOfMaster4[0])
        self.assertEqual(9, slotOfMaster4[1])

    def test_AFTER_AUTO_REBALANCE(self):
        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid')
        slotsInfo = master4.cluster('slots')

        groupByNode = groupby(slotsInfo, lambda s: s[2][2])
        allocation = []
        for nodeSlotsInfo in groupByNode:
            s = sum(slot[1] - slot[0] + 1 for slot in nodeSlotsInfo[1])
            allocation.append(s)
        self.assertEqual(4, len(allocation))
        self.assertEqual(1, len(set(allocation))) # balanced

    def test_AFTER_WEIGHTED_REBALANCE(self):
        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid')
        slotsInfo = master4.cluster('slots')

        groupByNode = groupby(slotsInfo, lambda s: s[2][2])
        allocation = []
        for nodeSlotsInfo in groupByNode:
            s = sum(slot[1] - slot[0] + 1 for slot in nodeSlotsInfo[1])
            allocation.append(s)
        norm = sorted([float(i)/min(allocation) for i in allocation])
        self.assertAlmostEqual(1, norm[0], places=2)
        self.assertAlmostEqual(2, norm[1], places=2)
        self.assertAlmostEqual(3, norm[2], places=2)
        self.assertAlmostEqual(4, norm[3], places=2) # weighted balanced

    def test_AFTER_SLAVE4_DELETED(self):
        nodes = master1.cluster("nodes")
        master_nodes = []
        slave_nodes = []
        for node in nodes.values():
            if 'master' in node['flags']:
                master_nodes.append(node)
            if 'slave' in node['flags']:
                slave_nodes.append(node)
        self.assertEqual(4, len(master_nodes))
        self.assertEqual(3, len(slave_nodes))

        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid').decode()
        output = master1.cluster('replicas', master4Id)
        self.assertEqual([], output)

    def test_AFTER_MOVE_ALL_SLOTS_IN_MASTER4(self):
        master4 = redis.Redis(host='localhost', port=46382)
        master4Id = master4.cluster('myid')
        slotsInfo = master4.cluster('slots')
        slotOfMaster4 = next((slot for slot in slotsInfo if slot[2][2] == master4Id), None)
        self.assertIsNone(slotOfMaster4)

    def test_AFTER_MASTER4_DELETED(self):
        nodes = master1.cluster("nodes")
        master_nodes = []
        slave_nodes = []
        for node in nodes.values():
            if 'master' in node['flags']:
                master_nodes.append(node)
            if 'slave' in node['flags']:
                slave_nodes.append(node)
        self.assertEqual(3, len(master_nodes))
        self.assertEqual(3, len(slave_nodes))


if __name__ == '__main__':
    unittest.main(verbosity=2)