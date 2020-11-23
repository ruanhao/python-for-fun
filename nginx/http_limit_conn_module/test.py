#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session
import threading

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "limit.hao.com"
})

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path



def client():
    print('thread %s is running...' % threading.current_thread().name)
    get(api('/'))
    print('thread %s ended.' % threading.current_thread().name)




class UnitTest(unittest.TestCase):

    def test_limit_conn(self):
        t = threading.Thread(target=client, name='First Client')
        t.start()
        r = get(api('/index.html'))
        self.assertEqual(500, r.status_code)






if __name__ == '__main__':
    unittest.main(verbosity=2)