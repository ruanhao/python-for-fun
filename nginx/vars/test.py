#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"
HOST = "vars.filter.hao.com"

s = Session()
s.headers.update({'Host': HOST})
get = s.get

def api(path):
    if path[0] in ['/', '?']:
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):

    def test_overall(self):
        r = get(api('?a=1&b=2'), cookies={'a': 'c'}, headers={'Content-Length': "0"})
        print(r.text)
        self.assertTrue('content_length: 0' in r.text)
        self.assertTrue('arg_a: 1,arg_b: 2, args: a=1&b=2' in r.text)
        self.assertTrue('cookie_a: c' in r.text)

    def test_map_vars(self):
        r = get(api('/mobile'), headers={'user-agent': "opera mini"})
        self.assertEqual("mobile: 0", r.text);
        r = get(api('/mobile'), headers={'user-agent': "Opera Mini"})
        self.assertEqual("mobile: 1", r.text);


    def test_map_vars_using_hostnames(self):
        r = get(api('/name'), headers={'Host': "map.hao.org"})
        self.assertEqual("map.hao.org: 2", r.text); # 泛域名表达式优先与正则表达式，前缀泛域名表达式优先于后缀泛域名表达式
        r = get(api('/name'), headers={'Host': "map.hao123.org"})
        self.assertEqual("map.hao123.org: 1", r.text);
        r = get(api('/name'), headers={'Host': "map.hao.com"})
        self.assertEqual("map.hao.com: 3", r.text); # 精确匹配优先级最高


    def test_split_clients(self):
        r = get(api('/number_level'), headers={'Number': "12345"})
        self.assertEqual("other", r.text);

        r = get(api('/number_level'), headers={'Number': "123456"})
        self.assertEqual("three", r.text);





if __name__ == '__main__':
    unittest.main(verbosity=2)