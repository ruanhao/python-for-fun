#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"
HOST = "upstream.hash.hao.com"

s = Session()
s.headers.update({'Host': HOST})
get = s.get

def api(path):
    if path[0] in ['/', '?']:
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):

    def test_iphash(self):
        for i in range(0, 10):
            r = get(api('/iphashups'), headers={'X-Forwarded-For': "100.200.20.200"})
            self.assertEqual("8012 server response", r.text)
            r = get(api('/iphashups'), headers={'X-Forwarded-For': "1.2.3.4"})
            self.assertEqual("8011 server response", r.text)


    def test_hash(self):

        for i in range(0, 10):
            r = get(api('/userhashups?username=Peter'))
            self.assertEqual("8011 server response", r.text)
            r = get(api('/userhashups?username=Cherry'))
            self.assertEqual("8012 server response", r.text)


if __name__ == '__main__':
    unittest.main(verbosity=2)