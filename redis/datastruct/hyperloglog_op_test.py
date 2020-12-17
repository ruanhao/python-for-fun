#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import time
import redis
import inspect
r = redis.Redis(host='localhost', port=46379, db=0)

def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'

def _used_memory_in_bytes():
    return r.info('memory')['used_memory']


class UnitTest(unittest.TestCase):


    def test_HyperLogLog(self):
        kSet = key()
        kHll = key()
        times = 1000
        m0 = _used_memory_in_bytes()
        for _ in range(0, times):
            r.sadd(kSet, str(uuid.uuid4()))
        m1 = _used_memory_in_bytes()
        for _ in range(0, times):
            r.pfadd(kHll, str(uuid.uuid4()))
        m2 = _used_memory_in_bytes()
        memory_used_by_set = m1 - m0
        memory_used_by_hll = m2 - m1
        print(f'\nMemory used by set: {memory_used_by_set}')
        print(f'Memory used by hll: {memory_used_by_hll}')
        self.assertTrue(memory_used_by_hll < memory_used_by_set)
        self.assertEqual(times, r.scard(kSet))
        print(f'pfcount: {r.pfcount(kHll)}')
        self.assertTrue(abs(times - r.pfcount(kHll)) / times <= 0.0081) # error rate 0.81%





if __name__ == '__main__':
    unittest.main(verbosity=2)