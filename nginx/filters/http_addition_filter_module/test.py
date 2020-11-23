#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"
HOST = "addition.filter.hao.com"

s = Session()
s.headers.update({'Host': HOST})
get = s.get

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):

    def test_add_before_body(self):
        r = get(api('/add_before_body/'))
        self.assertEqual(200, r.status_code)
        self.assertEqual('new content before\nindex (before)', r.text)

    def test_add_after_body(self):
        r = get(api('/add_after_body/'))
        self.assertEqual(200, r.status_code)
        self.assertEqual('index (after)new content after\n', r.text)





if __name__ == '__main__':
    unittest.main(verbosity=2)