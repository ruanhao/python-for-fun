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

    def test_query_by_boost(self):
        with self.subTest("Use boost parameter in match"):
            query = {
                'query': {
                    'bool': {
                        'should': [
                            {
                                'match': {
                                    'description': {
                                        'query': 'elasticsearch big data',
                                        # 'boost': 2.5
                                    }
                                }
                            },
                            {
                                'match': {
                                    'name': {
                                        'query': 'elasticsearch big data',
                                    }
                                }
                            },
                        ]
                    }
                }
            }
            r1 = es.search(query, INDEX)
            query['query']['bool']['should'][0]['match']['description']['boost'] = 2.5
            r2 = es.search(query, INDEX)
            self.assertEqual(r1['hits']['hits'][0]['_id'], r1['hits']['hits'][0]['_id'])
            self.assertGreater(r2['hits']['hits'][0]['_score'], r1['hits']['hits'][0]['_score'])

        with self.subTest("Specify boost for fields"):
            query = {
                'query': {
                    'multi_match': {
                        'query': 'elasticsearch big data',
                        "fields": ["name", "description"]

                    }
                }
            }
            r1 = es.search(query, INDEX)
            query['query']['multi_match']['fields'] = ["name", "description^3"]
            r2 = es.search(query, INDEX)
            self.assertEqual(r1['hits']['hits'][0]['_id'], r1['hits']['hits'][0]['_id'])
            self.assertGreater(r2['hits']['hits'][0]['_score'], r1['hits']['hits'][0]['_score'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
