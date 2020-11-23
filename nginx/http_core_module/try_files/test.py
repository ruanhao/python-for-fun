#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from requests import get, Session

# import logging
# logging.basicConfig(level=logging.DEBUG)

URL = "http://127.0.0.1:48080"

s = Session()
s.headers.update({
    'Host': "tryfiles.hao.com"
})


def api(path):
    if path[0] == '/':
        return URL + path
    else:
        return URL + '/' + path


class UnitTest(unittest.TestCase):


    def test_last_url(self):
        r = get(api('/lasturl'))
        self.assertEqual(200, r.status_code)
        self.assertEqual('lasturl', r.text)


    def test_last_code(self):
        r = get(api('/lastcode'))
        self.assertEqual(404, r.status_code)



    def test_found_file(self):
        r = get(api('/file-found'))
        self.assertEqual('file found', r.text.strip())





if __name__ == '__main__':
    unittest.main(verbosity=2)