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

    def test_append(self):
        k = random_key()
        r.set(k, "a")
        r.append(k, "b")
        self.assertEqual(b"ab", r.get(k))

    def test_strlen(self):
        k = random_key()
        r.set(k, "abc")
        self.assertEqual(3, r.strlen(k))

    def test_incr(self):
        k = random_key()
        r.set(k, "1")
        r.incr(k)
        self.assertEqual(b"2", r.get(k))

    def test_incrby(self):
        k = random_key()
        r.set(k, "1")
        r.incrby(k, 2)
        self.assertEqual(b"3", r.get(k))

    def test_getrange(self):
        k = random_key()
        r.set(k, "123456")
        self.assertEqual(b'123456', r.getrange(k, 0, -1))
        self.assertEqual(b'234', r.getrange(k, 1, 3))

    def test_setrange(self):
        k = random_key()
        r.set(k, "123456")
        r.setrange(k, 0, 'aaa')
        self.assertEqual(b'aaa456', r.get(k))
        r.setrange(k, 6, 'bbb') # append
        self.assertEqual(b'aaa456bbb', r.get(k))
        r.setrange(k, 10, 'ccc') # 超过长度
        self.assertEqual(b'aaa456bbb\x00ccc', r.get(k))


    def test_setex(self):
        k = random_key()
        r.setex(k, 2, "v")
        self.assertEqual(b'v', r.get(k))
        time.sleep(2)
        self.assertFalse(r.exists(k))

    def test_setnx(self):
        k = random_key()
        self.assertTrue(r.setnx(k, "v"))
        self.assertFalse(r.setnx(k, "v"))
        self.assertEqual(b'v', r.get(k))


    def test_msetnx(self):
        k1 = random_key()
        k2 = random_key()
        self.assertTrue(r.msetnx({k1: 'v1', k2: 'v2'})) # 必须都不存在，才能赋值成功
        self.assertEqual([b'v1', b'v2'], r.mget(k1, k2))
        k3 = random_key()
        self.assertFalse(r.msetnx({k2: 'v22', k3: 'v3'})) # 有一个存在，就不成功
        self.assertTrue(b'v22' !=  r.get(k2))


if __name__ == '__main__':
    unittest.main(verbosity=2)