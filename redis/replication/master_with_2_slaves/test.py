#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
master = redis.Redis(host='localhost', port=46379, db=0)
slave1 = redis.Redis(host='localhost', port=46380, db=0)
slave2 = redis.Redis(host='localhost', port=46381, db=0)

def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'



class UnitTest(unittest.TestCase):

    def test_repl(self):
        k = key()
        master.set(k, 'v')
        self.assertEqual(b'v', slave1.get(k))
        self.assertEqual(b'v', slave2.get(k))

    def test_readonly(self):
        with self.assertRaises(redis.exceptions.ReadOnlyError):
            slave1.set(key(), 'v2')

    def test_info_replication(self):
        self.assertEqual('master', master.info('replication')['role'])
        self.assertEqual('slave', slave1.info('replication')['role'])
        self.assertEqual('slave', slave2.info('replication')['role'])



if __name__ == '__main__':
    unittest.main(verbosity=2)