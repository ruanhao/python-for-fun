#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "rewrite.hao.com"
})

def api(path):
    return URL + path


class UnitTest(unittest.TestCase):


    def test_rewrite_last_and_break(self):
        r = s.get(api("/first/3.txt"))
        self.assertEqual("3", r.text.strip())


    def test_rewrite_last_and_no_break(self):
        r = s.get(api("/first/no_break/3.txt"))
        self.assertEqual("second", r.text.strip())


    def test_rewrite_permanent(self):
        r = s.get(api("/redirect1"))
        self.assertEqual(301, r.status_code)

    def test_rewrite_redirect(self):
        r = s.get(api("/redirect2"))
        self.assertEqual(302, r.status_code)

    def test_rewrite_redirect_with_uri(self):
        r = s.get(api("/redirect3/test"), allow_redirects=False)
        self.assertEqual(302, r.status_code)
        self.assertEqual("http://127.0.0.1/test", r.headers['Location'])


    def test_rewrite_redirect_with_uri_permanent(self):
        r = s.get(api("/redirect4/test"), allow_redirects=False)
        self.assertEqual(301, r.status_code)
        self.assertEqual("http://127.0.0.1/test", r.headers['Location'])




if __name__ == '__main__':
    unittest.main(verbosity=2)