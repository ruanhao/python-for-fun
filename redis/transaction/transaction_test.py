#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import uuid
import redis
import inspect
r = redis.Redis(host='localhost', port=46379, db=0)

def key():
    caller = inspect.stack()[1][3]
    return f'{caller}_key_{uuid.uuid4().hex[0:5]}'


# transaction = True 即表面使用 MULTI/EXEC (默认)

class UnitTest(unittest.TestCase):

    def test_MULTI_EXEC(self):
        k = key()
        pipe = r.pipeline()
        self.assertEqual([True, b'v'], pipe.set(k, 'v').get(k).execute())

        k2 = key()
        k3 = key()
        try:
            r.pipeline().set(k2, 'a').incr(k2).set(k3, 'b').execute()
            self.fail("cannot be here")
        except redis.exceptions.ResponseError as e:
            pass

        self.assertEqual(b'a', r.get(k2)) # 错误语句之前可以成功
        self.assertEqual(b'b', r.get(k3)) # 错误语句之后可以成功


    def test_WATCH(self):
        '''Watch the given keys to determine execution of the MULTI/EXEC block: WATCH key [key ...]'''
        watchedKey = key()
        r.set(watchedKey, 1)
        with r.pipeline() as pipe:
            pipe.watch(watchedKey)
            r.incr(watchedKey)           # watch 的值被修改了
            pipe.multi()
            pipe.set(key(), 'v')
            try:
                pipe.execute()  # 失败
                self.fail('cannot be here')
            except redis.exceptions.WatchError:
                pass

        with r.pipeline() as pipe:
            k2 = key()
            pipe.watch(watchedKey)
            pipe.multi()
            pipe.set(k2, 'v')
            self.assertEqual([True], pipe.execute())
            self.assertEqual(b'v', r.get(k2))





if __name__ == '__main__':
    unittest.main(verbosity=2)