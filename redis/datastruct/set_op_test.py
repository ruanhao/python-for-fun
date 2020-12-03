#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import time
import redis
import inspect
r = redis.Redis(host='localhost', port=46379, db=0)

def random_key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'


class UnitTest(unittest.TestCase):

    def test_sadd(self):
        k = random_key()
        r.sadd(k, 1, 1, 2, 2, 3, 3)
        self.assertEqual(3, len(r.smembers(k)))

    # Get the number of members in a set
    def test_scard(self):
        k = random_key()
        r.sadd(k, 1, 1, 2, 2, 3, 3)
        self.assertEqual(3, r.scard(k))

    def test_srem(self):
        k = random_key()
        r.sadd(k, 1, 1, 2, 2, 3, 3)
        r.srem(k, 3)
        self.assertEqual(2, r.scard(k))

    def test_srandmember(self):
        k = random_key()
        r.sadd(k, 1, 2, 3, 4, 5, 6)
        self.assertEqual(2, len(r.srandmember(k, 2)))
        while True:
            if b'3' in r.srandmember(k, 2):
                return

    # SPOP key [count]
    # Remove and return one or multiple random members from a set
    def test_spop(self):
        k = random_key()
        r.sadd(k, 1, 2, 3, 4, 5, 6)
        while True:
            if b'3' in r.spop(k, 2):
                return


    # SMOVE source destination member
    # Move a member from one set to another
    def test_smove(self):
        k1 = random_key()
        r.sadd(k1, 1, 2, 3, 4, 5, 6)
        k2 = random_key()
        r.smove(k1, k2, 3)
        self.assertTrue(b'3' not in r.smembers(k1))
        self.assertTrue(b'3' in r.smembers(k2))


    def test_sdiff(self):
        k1 = random_key()
        r.sadd(k1, 1, 2, 3)
        k2 = random_key()
        r.sadd(k2, 3, 4, 5)
        self.assertEqual(set([b'1', b'2']), r.sdiff(k1, k2))
        self.assertEqual(set([b'4', b'5']), r.sdiff(k2, k1))

    def test_sinter(self):
        k1 = random_key()
        r.sadd(k1, 1, 2, 3)
        k2 = random_key()
        r.sadd(k2, 3, 4, 5)
        self.assertEqual(set([b'3']), r.sinter(k1, k2))
        self.assertEqual(set([b'3']), r.sinter(k2, k1))

    def test_sunion(self):
        k1 = random_key()
        r.sadd(k1, 1, 2, 3)
        k2 = random_key()
        r.sadd(k2, 3, 4, 5)
        self.assertEqual(set([b'1', b'2', b'3', b'4', b'5']), r.sunion(k1, k2))
        self.assertEqual(set([b'1', b'2', b'3', b'4', b'5']), r.sunion(k2, k1))





if __name__ == '__main__':
    unittest.main(verbosity=2)