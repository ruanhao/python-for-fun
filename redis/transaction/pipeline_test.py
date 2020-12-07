#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
r = redis.Redis(host='localhost', port=46379, db=0)

def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_{uuid.uuid4().hex[0:5]}'


# transaction = False 即为普通 pipeline ，即不使用 MULTI/EXEC

class UnitTest(unittest.TestCase):

    def test_pipeline(self):
        k = key()
        pipe = r.pipeline(transaction=False)
        self.assertEqual([True, b'v'], pipe.set(k, 'v').get(k).execute())

        k2 = key()
        k3 = key()
        try:
            r.pipeline(transaction=False).set(k2, 'a').incr(k2).set(k3, 'b').execute()
            self.fail("cannot be here")
        except redis.exceptions.ResponseError as e:
            pass

        self.assertEqual(b'a', r.get(k2)) # 错误语句之前可以成功
        self.assertEqual(b'b', r.get(k3)) # 错误语句之后可以成功

if __name__ == '__main__':
    unittest.main(verbosity=2)