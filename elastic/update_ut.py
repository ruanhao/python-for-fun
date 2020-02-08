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

    def test_updating_partial_doc(self):
        r = es.get(INDEX, 1)
        self.assertTrue(r['found'])
        origin_desc = r['_source']['description']

        es.update(INDEX, 1, {'doc': {'name': 'test'}}, refresh=True)
        r = es.get(INDEX, 1)
        self.assertEqual('test', r['_source']['name'])
        self.assertEqual(origin_desc, r['_source']['description'])

    def test_upserting_doc(self):
        with self.assertRaises(NotFoundError):
            es.update(INDEX, 333, {'doc': {'name': 'test'}}, refresh=True)

        r = es.update(INDEX, 333, {'doc': {'name': 'test'}, 'doc_as_upsert': True}, refresh=True)
        self.assertEqual("created", r['result'])
        self.assertEqual("test", es.get(INDEX, 333)['_source']['name'])

    def test_updating_with_script(self):
        update = {
            'script': {
                "source": "ctx._source.tags.add(params.tag)",
                "lang": "painless",
                "params" : {
                    "tag" : "python"
                }
            }
        }
        r = es.update(INDEX, 1, update, refresh=True)
        self.assertEqual("updated", r['result'])
        self.assertIn('python', es.get(INDEX, 1)['_source']['tags'])

    def test_concurrency_control(self):
        index = _random_index()
        es.indices.create(index)
        es.index(index, {'price': 3}, id=1, refresh=True)
        update = {
            'doc': {
                'price': 5
            }
        }
        # use retry_on_conflict
        es.update(index, 1, update, retry_on_conflict=3)

        with self.subTest("External versioning"):
            r = es.get(index, 1)
            v = r['_version']
            with self.assertRaises(ConflictError):
                es.index(index, {'price': 5}, id=1, version=v, version_type='external')

            # external version must greater than current version
            es.index(index, {'price': 5}, id=1, version=v+1, version_type='external')

        with self.subTest("Internal versioning"):
            r = es.get(index, 1)
            seq_no = r['_seq_no']
            primary_term = r['_primary_term']
            with self.assertRaises(ConflictError):
                es.index(index, {'price': 5}, id=1, if_seq_no=1, if_primary_term=1)
            es.index(index, {'price': 5}, id=1, if_seq_no=seq_no, if_primary_term=primary_term)











if __name__ == '__main__':
    unittest.main(verbosity=2)
