#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import unittest
import datetime
import time
import warnings
import pymongo
from pprint import pprint
from mongodb_utils import *



class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="subprocess.*")


    def test_creating_replica_set(self):
        create_replica_set()


    def test_creating_replica_set_on_aws(self):
        c, rs_info = create_replica_set_on_aws()
        ts = datetime.datetime.now().timestamp()
        c.testdb.testcol.insert({"a": 1, 'ts': ts})
        d = c.testdb.testcol.find_one({'a': 1})
        self.assertEqual(d['ts'], ts)



if __name__ == '__main__':
    unittest.main(verbosity=2)