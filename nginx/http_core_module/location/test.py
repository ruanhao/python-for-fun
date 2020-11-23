#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "location.hao.com"
})

def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_exact_match(self):
        r = s.get(api("/Test1"))
        self.assertEqual("exact match", r.text)

    def test_stop_regex_match(self):
        '''
        ^~，= 可阻止 nginx 继续匹配正则，区别在于 ^~ 依然遵循最大前缀匹配规则，而 = 是严格匹配
        '''
        r = s.get(api("/Test1/"))
        self.assertEqual("stop regular expressions match", r.text)

    def test_regex_over_normal_match(self):
        '''
        虽然基于普通匹配(/Test1/Test2)可以匹配到，但仍会考虑正则匹配的结果。注意在这里，^~ /Test1/ 的最长前缀不如 /Test1/Test2 ，所以被排除
        '''
        r = s.get(api("/Test1/Test2"))
        self.assertEqual("longest regular expressions match", r.text)


    def test_merge_slashes(self):
        r = s.get(api("/a//b"))
        self.assertEqual(404, r.status_code)



if __name__ == '__main__':
    unittest.main(verbosity=2)