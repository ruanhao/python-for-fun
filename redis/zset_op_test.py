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

    #
    def test_ZRANGE(self):
        '''ZRANGE key start stop [WITHSCORES]'''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual([b'v1', b'v2', b'v3', b'v4', b'v5'], r.zrange(k, 0, -1))
        self.assertEqual([(b'v1', 60.0), (b'v2', 70.0), (b'v3', 80.0)], r.zrange(k, 0, 2, withscores=True))

    def test_ZREVRANGE(self):
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual([b'v5', b'v4', b'v3', b'v2', b'v1'], r.zrevrange(k, 0, -1))

    def test_ZRANGEBYSCORE(self):
        '''ZRANGEBYSCORE key [(]min [(]max [WITHSCORES] [LIMIT offset count]'''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual([b'v1', b'v2', b'v3'], r.zrangebyscore(k, 60, 80))
        self.assertEqual([b'v2', b'v3'], r.zrangebyscore(k, '(60', 80))
        self.assertEqual([b'v2'], r.zrangebyscore(k, '(60', '(80'))
        self.assertEqual([b'v2', b'v3'], r.zrangebyscore(k, '60', '100', start=1, num=2))


    def test_ZREVRANGEBYSCORE(self):
        '''
        ZREVRANGEBYSCORE key [(]max [(]min [WITHSCORES] [LIMIT offset count]
        '''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual([b'v3', b'v2', b'v1'], r.zrevrangebyscore(k, 80, 60))


    def test_ZCARD(self):
        '''Get the number of members in a sorted set'''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual(5, r.zcard(k))

    def test_ZCOUNT(self):
        '''
        Count the members in a sorted set with scores within the given values: ZCOUNT key [(]min [(]max
        '''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual(3, r.zcount(k, 60, 80))
        self.assertEqual(2, r.zcount(k, '(60', 80))
        self.assertEqual(1, r.zcount(k, '(60', '(80'))

    def test_ZRANK(self):
        '''
        Determine the index of a member in a sorted set: ZRANK key member
        '''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual(2, r.zrank(k, 'v3'))

    def test_ZREVRANK(self):
        '''
        Determine the index of a member in a sorted set, with scores ordered from high to low
        '''
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual(1, r.zrevrank(k, 'v4'))

    def test_ZSCORE(self):
        k = key()
        r.zadd(k, {'v2': 70, 'v1': 60, 'v4': 90, 'v3': 80, 'v5': 10, 'v5': 100})
        self.assertEqual(80.0, r.zscore(k, 'v3'))



if __name__ == '__main__':
    unittest.main(verbosity=2)