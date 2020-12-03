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


class UnitTest(unittest.TestCase):

    def test_hlen(self):
        k = key()
        r.hset(k, 'k1', 'v1')
        r.hset(k, 'k2', 'v2')
        self.assertEqual(2, r.hlen(k))

    def test_hexists(self):
        k = key()
        r.hset(k, 'k1', 'v1')
        r.hset(k, 'k2', 'v2')
        self.assertTrue(r.hexists(k, 'k1'))
        self.assertFalse(r.hexists(k, 'k3'))


    def test_hkeys(self):
        k = key()
        r.hset(k, 'k1', 'v1')
        self.assertEqual([b'k1'], r.hkeys(k))

    def test_hvals(self):
        k = key()
        r.hset(k, 'k1', 'v1')
        self.assertEqual([b'v1'], r.hvals(k))

    # HINCRBY key field increment
    def test_hincrby(self):
        k = key()
        r.hset(k, 'age', 30)
        r.hincrby(k, 'age', 5)
        self.assertEqual(b'35', r.hget(k, 'age'))


    def test_hincrbyfloat(self):
        k = key()
        r.hset(k, 'height', 180)
        r.hincrbyfloat(k, 'height', 3.5)
        self.assertEqual(b'183.5', r.hget(k, 'height'))

    def test_hsetnx(self):
        k = key()
        r.hsetnx(k, 'name', 'peter')
        self.assertEqual(b'peter', r.hget(k, 'name'))
        self.assertFalse(r.hsetnx(k, 'name', 'mary'))
        self.assertEqual(b'peter', r.hget(k, 'name'))


if __name__ == '__main__':
    unittest.main(verbosity=2)