#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import os
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import RequestError
from pprint import pprint
import uuid


es = Elasticsearch()


def _random_index():
    return str(uuid.uuid4())


class UnitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.system("curl -s -X DELETE localhost:9200/_all >/dev/null")
        # os.system("bash ./populate.sh >/dev/null")

    @classmethod
    def tearDownClass(cls):
        pass

    def test_getting_mapping(self):
        index = _random_index()
        r = es.indices.create(index)
        self.assertTrue(r['acknowledged'])
        pprint(es.indices.get_mapping(index))

    def test_extending_existing_mapping(self):
        """
        When you put a mapping over an existing one, Elasticsearch merges the two.
        """
        index = _random_index()
        es.indices.create(index)
        body = {
            'properties': {
                'test': {
                    'type': 'text'
                },
            }
        }
        result = es.indices.put_mapping(body, index)
        self.assertTrue(result['acknowledged'])
        self.assertEqual(es.indices.get_mapping(index)[index]['mappings']['properties']['test']['type'], 'text')

        body = {
            'properties': {
                'test2': {
                    'type': 'text'
                },
            }
        }
        es.indices.put_mapping(body, index)
        self.assertEqual(es.indices.get_mapping(index)[index]['mappings']['properties']['test']['type'], 'text',
                         "There should be other properties which are already defined")

        body2 = {
            'properties': {
                'test': {
                    'type': 'integer'
                }
            }
        }

        with self.assertRaises(RequestError) as e:
            es.indices.put_mapping(body2, index)

        self.assertEqual("illegal_argument_exception", e.exception.error,
                         "Can't change an existing field's data type, and, "
                         "in general, you can't change the way a field is indexed.")

    def test_multi_fields(self):
        """
        Multi fields are about indexing the same date multiple times using different settings.
        """
        index = _random_index()
        body = {
                'mappings': {
                    'properties': {
                        'name': {
                            'type': 'text',
                            'fields': {
                                'foo': {
                                    'type': 'text',
                                },
                                'bar': {
                                    'type': 'text',
                                    'index': False,
                                },

                            }
                        },
                    }
                }
            }
        r = es.indices.create(index=index, body=body)
        self.assertTrue(r['acknowledged'])
        r = es.index(index=index, body={'name': "hello"}, refresh=True)
        self.assertEqual('created', r['result'])

        query = {
            "query": {
                "match": {
                    "name": {
                        'query': 'hello'
                    }
                },
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(1, r['hits']['total']['value'])

        query = {
            "query": {
                "match": {
                    "name.foo": {
                        'query': 'hello'
                    }
                },
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(1, r['hits']['total']['value'])

        query = {
            "query": {
                "match": {
                    "name.bar": {
                        'query': 'hello'
                    }
                },
            }
        }
        with self.assertRaises(RequestError):
            es.search(index=index, body=query)

    def test_mapping_parameters(self):
        with self.subTest("index"):
            """
            https://www.elastic.co/guide/en/elasticsearch/reference/master/mapping-index.html
            """
            index = _random_index()
            body = {
                'mappings': {
                    'properties': {
                        'name': {
                            'type': 'text',
                            'index': False
                        },
                        'company': {
                            'type': 'text',
                        }
                    }
                }
            }
            r = es.indices.create(index=index, body=body)
            self.assertTrue(r['acknowledged'])
            r = es.index(index=index, body={'name': "hello", 'company': 'cisco'}, refresh=True)
            self.assertEqual('created', r['result'])
            query = {
                "query": {
                    "multi_match": {
                        "query": "cisco",
                    },
                }
            }
            r = es.search(index=index, body=query)
            self.assertEqual(1, r['hits']['total']['value'])

            query = {
                "query": {
                    "multi_match": {
                        "query": "hello",
                    },
                }
            }
            r = es.search(index=index, body=query)
            self.assertEqual(0, r['hits']['total']['value'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
