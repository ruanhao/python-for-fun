#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "return.hao.com"
})


class UnitTest(unittest.TestCase):


    def test_static_file(self):
        r = s.get(URL + '/hello.html')
        self.assertEqual("hello page", r.text)

    def test_500(self):
        r = s.get(URL + '/error/500')
        self.assertEqual("500 page", r.text)

    def test_no_existent_file(self):
        r = s.get(URL + '/non-existent.html')
        self.assertEqual("404 page", r.text)

    def test_500_with_msg(self):
        r = s.get(URL + '/error/500/msg')
        self.assertEqual("500 directive", r.text)

    def test_501(self):
        r = s.get(URL + '/error/501')
        self.assertEqual(200, r.status_code)
        self.assertEqual("501 page", r.text)

    def test_internal_jump(self):
        r = s.get(URL + '/fallback/no_existence.html')
        self.assertEqual(503, r.status_code)




if __name__ == '__main__':
    unittest.main(verbosity=2)