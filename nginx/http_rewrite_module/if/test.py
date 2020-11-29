#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "if.hao.com"
})

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_regex_case_sensitive(self):
        r = s.get(api("/regex-case-sensitive"), headers={'User-Agent': 'MACOS'})
        self.assertEqual(200, r.status_code)
        r = s.get(api("/regex-case-sensitive"), headers={'User-Agent': 'macos'})
        self.assertEqual(400, r.status_code)

    def test_regex_case_insensitive(self):
        r = s.get(api("/regex-case-insensitive"), headers={'User-Agent': 'MACOS'})
        self.assertEqual(200, r.status_code)
        r = s.get(api("/regex-case-insensitive"), headers={'User-Agent': 'macos'})
        self.assertEqual(200, r.status_code)


    def test_evil_if(self):
        r = s.get(api("/evil/if"))
        self.assertFalse('X-FIRST-HEADER' in r.headers)
        self.assertFalse('X-ORIGIN-HEADER' in r.headers)
        self.assertTrue('X-SECOND-HEADER' in r.headers)
        self.assertEqual("str: aaa", r.text)


    def test_evil_if_break(self):
        r = s.get(api("/evil/if/break"))
        self.assertTrue('X-FIRST-HEADER' in r.headers)
        self.assertFalse('X-SECOND-HEADER' in r.headers)



if __name__ == '__main__':
    unittest.main(verbosity=2)