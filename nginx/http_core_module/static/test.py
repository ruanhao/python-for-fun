#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "static.hao.com"
})


def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_root(self):
        r = s.get(api('/root/'))
        self.assertEqual(404, r.status_code) # error_log: "/vagrant/html/root/index.html" is not found

        r = s.get(api('/root/1.txt'))
        self.assertEqual(404, r.status_code) # error_log: open() "/vagrant/html/first/1.txt/root/1.txt" failed


    def test_alias(self):
        r = s.get(api('/alias/'))
        self.assertEqual(200, r.status_code)
        self.assertEqual('index', r.text.strip())

        r = s.get(api('/alias/1.txt'))
        self.assertEqual(200, r.status_code)
        self.assertEqual('1', r.text.strip())


    def test_embeded_variable(self):
        r = s.get(api('/RealPath/1.txt'))
        self.assertEqual('/vagrant/html/realpath/1.txt:/vagrant/html/realpath/:/vagrant/html/first', r.text)


    def test_absolute_redirect_off(self): # 先在 html 创建 absolute-redirect-off 目录
        # 因为 absolute-redirect-off 是目录，所以如果不以 / 结尾的方式访问，会产生跳转（指向以 / 结尾的形式）
        r = s.get(api('/absolute-redirect-off'), allow_redirects=False)
        self.assertEqual('/absolute-redirect-off/', r.headers['location'])


    def test_absolute_redirect_on(self): # 先在 html 创建 absolute-redirect-on 目录
        # 因为 absolute-redirect-on 是目录，所以如果不以 / 结尾的方式访问，会产生跳转（指向以 / 结尾的形式）
        r = s.get(api('/absolute-redirect-on'), allow_redirects=False)
        self.assertEqual('http://static.hao.com:8080/absolute-redirect-on/', r.headers['location'])


    def test_server_name_in_redirect_off(self): # 先在 html 创建 server_name_in_redirect_off 目录
        r = s.get(api('/server_name_in_redirect_off'), allow_redirects=False)
        self.assertEqual('http://static.hao.com:8080/server_name_in_redirect_off/', r.headers['location'])

        r = s.get(api('/server_name_in_redirect_off'), allow_redirects=False, headers={'Host': "aaa"})
        self.assertEqual('http://aaa:8080/server_name_in_redirect_off/', r.headers['location'])


    def test_server_name_in_redirect_on(self): # 先在 html 创建 server_name_in_redirect_on 目录
        r = s.get(api('/server_name_in_redirect_on'), allow_redirects=False)
        self.assertEqual('http://static.hao.com:8080/server_name_in_redirect_on/', r.headers['location'])

        r = s.get(api('/server_name_in_redirect_on'), allow_redirects=False, headers={'Host': "abc"})
        self.assertEqual('http://static.hao.com:8080/server_name_in_redirect_on/', r.headers['location'])


    def test_port_in_redirect_off(self): # 先在 html 创建 port_in_redirect_off 目录
        r = s.get(api('/port_in_redirect_off'), allow_redirects=False)
        self.assertEqual('http://static.hao.com/port_in_redirect_off/', r.headers['location'])


    def test_port_in_redirect_on(self): # 先在 html 创建 port_in_redirect_on 目录
        r = s.get(api('/port_in_redirect_on'), allow_redirects=False)
        self.assertEqual('http://static.hao.com:8080/port_in_redirect_on/', r.headers['location'])





if __name__ == '__main__':
    unittest.main(verbosity=2)