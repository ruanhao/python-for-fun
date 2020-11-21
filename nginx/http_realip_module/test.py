#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get

URL = "http://127.0.0.1:48080"
HEADERS = {
    'Host': "realip.hao.com"
}

class UnitTest(unittest.TestCase):


    def test_real_ip(self):
        r = get(URL, headers={**HEADERS, 'X-Forwarded-For': "1.2.3.4,5.6.7.8"})
        self.assertEqual("Client REAL IP: 5.6.7.8", r.text)






if __name__ == '__main__':
    unittest.main(verbosity=2)