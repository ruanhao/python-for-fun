#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "auth.req.hao.com"
})


def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_auth_req_success(self):
        r = get(api('/'))
        self.assertEqual(200, r.status_code)


    def test_auth_req_unauthorized(self):
        r = get(api('/test.html'))
        self.assertEqual(401, r.status_code)



if __name__ == '__main__':
    unittest.main(verbosity=2)