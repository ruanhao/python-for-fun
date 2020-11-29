#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"
HOST = "upstream.proxy.hao.com"

s = Session()
s.headers.update({'Host': HOST})
get = s.get

def api(path):
    if path[0] in ['/', '?']:
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):

    def test_proxy_without_url(self):
        r = get(api('/proxy_without_url/a/b/c'))
        print(r.text)
        self.assertTrue('uri: /proxy_without_url/a/b/c' in r.text)


    def test_proxy_with_url(self):
        r = get(api('/proxy_with_url/a/b/c'))
        print(r.text)
        self.assertTrue('uri: /test/a/b/c' in r.text)


    def test_proxy_method(self):
        r = get(api('/change_proxy_method'))
        print(r.text)
        self.assertTrue('method: POST' in r.text)

    def test_proxy_set_body(self):
        r = get(api('/proxy_set_body'))
        print(r.text)
        self.assertTrue('content-length: 11' in r.text)








if __name__ == '__main__':
    unittest.main(verbosity=2)