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
        # os.system("curl -s -X DELETE localhost:9200/_all >/dev/null")
        # os.system("bash ./populate.sh >/dev/null")
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test_analyzing(self):
        body = {
            "analyzer" : "standard",
            "text" : "I love Bears and Fish.",
        }
        r = es.indices.analyze(body)
        self.assertEqual(5, len(r['tokens']))

        with self.subTest("Customize tokenizer and filter"):
            """
            Cannot define extra components on a named analyzer
            """
            body = {
                "text" : "I love Bears and Fish.",
                'tokenizer': 'whitespace',
                'filter': ['lowercase', 'reverse']
            }
            r = es.indices.analyze(body)
            self.assertEqual(".hsif", r['tokens'][-1]['token'])

        with self.subTest("Analyzing based on a field's mapping"):
            index = _random_index()
            settings = {
                'mappings': {
                    'properties': {
                        'description': {
                            'type': 'text',
                            'analyzer': 'italian'
                        },
                    }
                }
            }
            es.indices.create(index=index, body=settings)
            a_body = {
                'text': "Era deliziosa",
                'field': 'description'
            }
            r = es.indices.analyze(a_body, index)
            self.assertEqual(1, len(r['tokens']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
