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

    def test_match_all(self):
        query = {
            'query': {
                'match_all': {
                }
            }
        }
        query_with_filter = {
            'query': {
                'bool': {
                    'must': {
                        'match_all': {}
                    },
                    'filter': {
                        'term': {
                            'tags': 'lucene'
                        }
                    }
                }
            }

        }
        r1 = es.search(index=INDEX, body=query)
        r2 = es.search(index=INDEX, body=query_with_filter)
        self.assertLess(r2['hits']['total']['value'], r1['hits']['total']['value'])

    def test_combining_query(self):
        """
        Search for events that were attended by David,
        and must be attended by either Clint or Andy,
        and must not be older than June 30, 2013.
        """
        query = {
            'query': {
                'bool': {
                    'must': [
                        {
                            'term': {
                                'attendees': 'david'
                            }
                        },
                        {
                            'range': {
                                'date': {
                                    'gt': '2013-06-30T00:00'
                                }
                            }
                        }
                    ],
                    'should': [
                        {
                            'terms': {
                                'attendees': ["clint", "andy"]
                            }
                        }
                    ],
                    "minimum_should_match": 1
                },
            }
        }
        r = es.search(index=INDEX, body=query)
        self.assertEqual(1, r['hits']['total']['value'])

    def test_match_bool_behaviour(self):
        """
        By default, the match query uses Boolean behavior and the OR operator.
        For example, if you search for the text "Elasticsearch Denver," Elasticsearch searches for "Elasticsearch OR Denver,"
        which would match get-togethers from both "Elasticsearch Amsterdam" and "Denver Clojure Group".

        To search for results that contain both "Elasticsearch" and "Denver",
        change the operator by modifying the match field name into a map and set the operator field to and.
        """
        query_or = {
            'query': {
                'match': {
                    'name': {
                        'query': "Elasticsearch Denver",
                    }
                }
            }
        }
        r_or = es.search(index=INDEX, body=query_or)

        query_and = {
            'query': {
                'match': {
                    'name': {
                        'query': "Elasticsearch Denver",
                        'operator': "and"
                    }
                }
            }
        }
        r_and = es.search(index=INDEX, body=query_and)

        self.assertLess(r_and['hits']['total']['value'], r_or['hits']['total']['value'])

    def test_match_phrase(self):
        index = _random_index()
        es.indices.create(index)
        es.index(index, {'title': "this is not a test"}, refresh=True)
        es.index(index, {'title': "this is really a test"}, refresh=True)
        es.index(index, {'title': "this is really not a test"}, refresh=True)

        query = {
            "query": {
                "match_phrase": {
                    "title": "this is"
                }
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(3, r['hits']['total']['value'])

        query = {
            "query": {
                "match_phrase": {
                    "title": "this is a"
                }
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(0, r['hits']['total']['value'])

        query = {
            "query": {
                "match_phrase": {
                    "title": {
                        "query": "this is a",
                        "slop": 1
                    }
                }
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(2, r['hits']['total']['value'])

        query = {
            "query": {
                "match_phrase": {
                    "title": {
                        "query": "this is a",
                        "slop": 2
                    }
                }
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(3, r['hits']['total']['value'])

    def test_match_phrase_prefix(self):
        index = _random_index()
        es.indices.create(index)
        es.index(index, {'title': "this is cat"}, refresh=True)
        es.index(index, {'title': "this is camera"}, refresh=True)
        es.index(index, {'title': "this is catalina"}, refresh=True)

        query = {
            "query": {
                "match_phrase_prefix": {
                    "title": {
                        'query': "this is ca",
                        'max_expansions': 1
                    }
                }
            }
        }
        r = es.search(index=index, body=query)
        self.assertEqual(1, r['hits']['total']['value'])

        query['query']['match_phrase_prefix']['title']['max_expansions'] = 2
        r = es.search(index=index, body=query)
        self.assertEqual(2, r['hits']['total']['value'])

        query['query']['match_phrase_prefix']['title']['max_expansions'] = 10
        r = es.search(index=index, body=query)
        self.assertEqual(3, r['hits']['total']['value'])

    def test_explain(self):
        query = {
            'query': {
                'match': {
                    'name': {
                        'query': "Elasticsearch",
                    }
                }
            }
        }
        r = es.search(query, INDEX, explain=True)
        self.assertIn('_explanation', r['hits']['hits'][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
