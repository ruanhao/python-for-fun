#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
from itertools import groupby
master1 = redis.Redis(host='localhost', port=46379, db=0)

MASTER_1_IP = '192.168.33.11'
MASTER_2_IP = '192.168.33.12'
MASTER_3_IP = '192.168.33.13'

def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'


class UnitTest(unittest.TestCase):

    def test_HASHTAG(self):
        slots = []
        for i in range(10):
            k = key() + '{sameslot}'
            slot = master1.cluster('keyslot', k)
            slots.append(slot)
        self.assertEqual(10, len(slots))
        self.assertEqual(1, len(set(slots)))


    def test_MOVED(self):
        with self.assertRaises(redis.exceptions.ResponseError) as e:
            master1.set('a', 1)
        self.assertTrue('MOVED' in str(e.exception))




if __name__ == '__main__':
    unittest.main(verbosity=2)