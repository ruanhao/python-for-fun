#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "sub.hao.com"
})
get = s.get

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_sub_filter_once_on(self):
        r = get(api('/sub_filter_once_on/'))
        self.assertEqual(200, r.status_code)
        self.assertEqual("hi hello sub.hao.com/nginx", r.text.strip())

    def test_sub_filter_once_off(self):
        r = get(api('/sub_filter_once_off/'))
        self.assertEqual(200, r.status_code)
        self.assertEqual("hi hi sub.hao.com/nginx", r.text.strip())

    def test_sub_filter_last_modified_on(self):
        r = get(api('/sub_filter_last_modified_on/'))
        self.assertEqual(200, r.status_code)
        self.assertTrue('last-modified' in r.headers)

    def test_sub_filter_last_modified_off(self):
        r = get(api('/sub_filter_last_modified_off/'))
        self.assertEqual(200, r.status_code)
        self.assertTrue('last-modified' not in r.headers)








if __name__ == '__main__':
    unittest.main(verbosity=2)