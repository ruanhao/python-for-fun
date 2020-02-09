#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from elasticsearch.exceptions import NotFoundError
from elasticsearch.exceptions import ConflictError
from pprint import pprint
import uuid


es = Elasticsearch()

INDEX = 'get-together'


def _random_index():
    i = str(uuid.uuid4())
    # print(f'Random index generated: {i}')
    return i


class UnitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.system("curl -s -X DELETE localhost:9200/_all >/dev/null")
        os.system("bash ./populate.sh >/dev/null")

    @classmethod
    def tearDownClass(cls):
        pass

    def test_deleting_doc_by_id(self):
        r = es.delete(INDEX, id=102)
        self.assertEqual('deleted', r['result'])









if __name__ == '__main__':
    unittest.main(verbosity=2)
