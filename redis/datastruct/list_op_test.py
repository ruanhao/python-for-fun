#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import time
import redis
r = redis.Redis(host='localhost', port=46379, db=0)

def random_key():
    return uuid.uuid4().hex


class UnitTest(unittest.TestCase):

    def test_push(self):
        k = random_key()
        self.assertEqual(3, r.lpush(k, 1, 2, 3))
        self.assertEqual(6, r.rpush(k, 'a', 'b', 'c'))

    def test_pop(self):
        k = random_key()
        self.assertEqual(3, r.lpush(k, 1, 2, 3))
        self.assertEqual(6, r.rpush(k, 'a', 'b', 'c'))
        # 3 2 1 a b c
        self.assertEqual(b'3', r.lpop(k))
        self.assertEqual(b'c', r.rpop(k))
        self.assertEqual([b'2', b'1', b'a', b'b'], r.lrange(k, 0, -1))

    def test_lrange(self):
        k = random_key()
        self.assertEqual(3, r.lpush(k, 1, 2, 3))
        self.assertEqual([b'3', b'2', b'1'], r.lrange(k, 0, -1))

        self.assertEqual(6, r.rpush(k, 'a', 'b', 'c'))
        self.assertEqual([b'3', b'2', b'1', b'a', b'b', b'c'], r.lrange(k, 0, -1))

    def test_lindex(self):
        k = random_key()
        self.assertEqual(3, r.lpush(k, 1, 2, 3))
        # 3 2 1
        self.assertEqual(b'3', r.lindex(k, 0))
        self.assertEqual(None, r.lindex(k, 3))

    def test_llen(self):
        k = random_key()
        self.assertEqual(3, r.lpush(k, 1, 2, 3))
        self.assertEqual(3, r.llen(k))

    # 删除 N 个值
    # LREM key count value
    def test_lrem(self):
        k = random_key()
        self.assertEqual(9, r.rpush(k, 1, 1, 1, 2, 2, 2, 3, 3, 3))
        self.assertEqual(2, r.lrem(k, 2, 3))
        self.assertEqual([b'1', b'1', b'1', b'2', b'2', b'2', b'3'], r.lrange(k, 0, -1))

    # 截取指定范围的值，再赋值给该 key
    # LTRIM key start stop
    def test_ltrim(self):
        k = random_key()
        self.assertEqual(9, r.rpush(k, 1, 1, 1, 2, 2, 2, 3, 3, 3))
        self.assertTrue(r.ltrim(k, 0, 2))
        self.assertEqual([b'1', b'1', b'1'], r.lrange(k, 0, -1))

    # RPOPLPUSH source destination
    def test_rpoplpush(self):
        k1 = random_key()
        k2 = random_key()
        self.assertEqual(3, r.rpush(k1, 1, 2, 3))
        r.rpoplpush(k1, k2)
        self.assertEqual([b'1', b'2'], r.lrange(k1, 0, -1))
        self.assertEqual([b'3'], r.lrange(k2, 0, -1))

        r.rpoplpush(k1, k2)
        self.assertEqual([b'1'], r.lrange(k1, 0, -1))
        self.assertEqual([b'2', b'3'], r.lrange(k2, 0, -1))

    def test_lset(self):
        k = random_key()
        r.rpush(k, 1, 2, 3)
        r.lset(k, 2, 'x')
        self.assertEqual([b'1', b'2', b'x'], r.lrange(k, 0, -1))

    # LINSERT key BEFORE|AFTER pivot value
    def test_linsert(self):
        k = random_key()
        r.rpush(k, 1, 2, 3)
        r.linsert(k, 'BEFORE', 2, 'a')
        self.assertEqual([b'1', b'a', b'2', b'3'], r.lrange(k, 0, -1))
        r.linsert(k, 'AFTER', 2, 'b')
        self.assertEqual([b'1', b'a', b'2', b'b', b'3'], r.lrange(k, 0, -1))




if __name__ == '__main__':
    unittest.main(verbosity=2)