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

    def test_keys(self):
        k = random_key()
        r.set(k, 1)
        self.assertTrue(k.encode() in r.keys())

    def test_exists(self):
        k = random_key()
        r.set(k, 1)
        self.assertTrue(r.exists(k))

    def test_expire_ttl(self):
        k = random_key()
        r.set(k, 1)
        r.expire(k, 3)
        time.sleep(1)
        self.assertEqual(2, r.ttl(k))
        time.sleep(2)
        self.assertFalse(r.exists(k))

    def test_type(self):
        stringKey = random_key()
        r.set(stringKey, 1, ex=3)
        self.assertEqual(b'string', r.type(stringKey))

        listKey = random_key()
        r.lpush(listKey, 1, 2, 3)
        self.assertEqual(b'list', r.type(listKey))

        hashKey = random_key()
        r.hset(hashKey, random_key(), 1)
        self.assertEqual(b'hash', r.type(hashKey))



if __name__ == '__main__':
    unittest.main(verbosity=2)