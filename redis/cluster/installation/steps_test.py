#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
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


if __name__ == '__main__':
    unittest.main(verbosity=2)