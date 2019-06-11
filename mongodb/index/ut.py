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

db = get_client().test_index

class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
        warnings.filterwarnings("ignore", category=ResourceWarning, message="subprocess.*")


    def test_single_field_index(self):
        collection = db['records']
        collection.drop()

        data = [
            {
                "score": 1034,
                "location": { "state": "NY", "city": "New York" }
            },
            {
                "score": 1035,
                "location": { "state": "SH", "city": "Shanghai" }
            },
            {
                "score": 2035,
                "location": { "state": "SJ", "city": "San Jose" }
            },
        ]
        collection.insert_many(data)
        ###


        with self.subTest("Create an Index on a Single Field"):
            collection.create_index([('score', pymongo.ASCENDING)])


        with self.subTest("Create an Index on an Embedded Field"):
            collection.create_index([('location.state', pymongo.ASCENDING)])


        with self.subTest("Create an Index on Embedded Document"):
            collection.create_index([('location', pymongo.ASCENDING)])
            document = collection.find_one({'location': {'state': 'SJ', 'city': 'San Jose'}})
            self.assertEqual(document['score'], 2035)

    def test_compound_index(self):
        '''
        The index will contain references to documents sorted first by the values of the 'item' field and,
        within each value of the 'item' field, sorted by values of the stock field.
        '''
        collection = db['products']
        collection.drop()
        collection.insert_one({
            "item": "Banana",
            "category": ["food", "produce", "grocery"],
            "location": "4th Street Store",
            "stock": 4,
            "type": "cases"
        })
        ###

        collection.create_index([('item', pymongo.ASCENDING), ('stock', pymongo.ASCENDING)])


    def test_text_index(self):
        collection = db['blog']
        collection.drop()
        collection.insert_many([
            {
                "_id": 1,
                "content": "This morning I had a cup of coffee and some dessert.",
                "about": "beverage and food",
                "keywords": [ "coffee" ]
            },

            {
                "_id": 2,
                "content": "Who doesn't like cake?",
                "about": "food",
                "keywords": [ "cake", "food", "dessert" ]
            }
        ])
        ###
        collection.create_index([
            ('content', pymongo.TEXT),
            ('keywords', pymongo.TEXT),
            ('about', pymongo.TEXT)], weights={
                'content': 10,
                'keywords': 5,
                # 'about' has the default weight of 1.
        })

        # content field has:
        # - 2 times (i.e. 10:5) the impact as a term match in the keywords field and
        # - 10 times (i.e. 10:1) the impact as a term match in the about field.

        documents = list(collection.find({'$text': {'$search': "food"}}))
        print('Find by "food":')
        pprint(documents)
        self.assertEqual(documents[0]['_id'], 2)
        documents = list(collection.find({'$text': {'$search': "dessert"}}))
        print('Find by "desert":')
        pprint(documents)
        self.assertEqual(documents[0]['_id'], 1)


    def test_index_properties(self):
        # with self.subTest("Expire Documents after a Specified Number of Seconds"):
        #     collection = db['ttl.seconds']
        #     collection.drop()
        #     collection.insert_many([
        #         {'lastModifiedDate': datetime.datetime.utcnow()},
        #         {'lastModifiedDate': datetime.datetime.utcnow()},
        #         {'lastModifiedDate': datetime.datetime.utcnow()},
        #     ])
        #     ###
        #     collection.create_index([('lastModifiedDate', pymongo.ASCENDING)], expireAfterSeconds=3)
        #     time.sleep(60)      # The background task that removes expired documents runs every 60 seconds
        #     self.assertEqual(list(collection.find({})), [])


        # with self.subTest("Expire Documents at a Specific Clock Time"):
        #     collection = db['ttl.specific']
        #     collection.drop()
        #     diff = datetime.timedelta(seconds=3)
        #     collection.insert_many([
        #         {'expireAt': datetime.datetime.utcnow() + diff},
        #         {'expireAt': datetime.datetime.utcnow() + diff},
        #         {'expireAt': datetime.datetime.utcnow() + diff},
        #         {'expireAt': datetime.datetime.utcnow() - diff},
        #     ])
        #     ###
        #     self.assertEqual(len(list(collection.find({}))), 4)
        #     collection.create_index([('expireAt', pymongo.ASCENDING)], expireAfterSeconds=0)
        #     time.sleep(60)
        #     self.assertEqual(list(collection.find({})), [])

        with self.subTest("Unique Index"):
            collection = db['uniq.students']
            collection.drop()
            collection.insert_many([
                {'name': "Peter"},
            ])
            ###

            collection.create_index([('name', pymongo.ASCENDING)], unique=True)
            collection.insert_one({'name': "Mary"})
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                collection.insert_one({'name': "Peter"})

        with self.subTest("Partial Index"):
            '''
            Partial indexes only index the documents in a collection that meet a specified filter expression.
            By indexing a subset of the documents in a collection, partial indexes have lower storage requirements
            and reduced performance costs for index creation and maintenance.

            Partial indexes represent a superset of the functionality offered by sparse indexes and should be PREFERRED OVER SPARSE INDEXES.
            '''
            collection = db['partial.restaurants']
            collection.drop()
            collection.insert_many([
                {'name': "Vs", 'rating': 10},
                {'name': "Tsui Wha", 'rating': 3},
                {'name': "Wang Steak", 'rating': 8},
            ])
            ###
            index_name = collection.create_index([('rating', pymongo.ASCENDING)], partialFilterExpression={'rating': {'$gt': 5}})
            # MongoDB will not use the partial index for a query or sort operation if using the index results in an incomplete result set.
            # To use the partial index, a query must contain filter expression that specifies a SUBSET of the filter expression as part of its query condition.
            collection.find_one({'name': 'Vs', 'rating': {'$gt': 8}})  # parital index used
            collection.find_one({'name': 'Tsui Wha', 'rating': {'$lt': 8}})  # parital index not used
            collection.find_one({'name': 'Tsui Wha'})  # parital index not used

            collection.drop_index(index_name)
            collection.create_index([('name', pymongo.ASCENDING)], partialFilterExpression={'rating': {'$gt': 5}}, unique=True)
            collection.insert_one({'name': "Vs", 'rating': 2})
            collection.insert_one({'name': "Vs"})
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                collection.insert_one({'name': "Vs", 'rating': 30})




        with self.subTest("Sparse Index"):
            '''
            Sparse indexes only contain entries for documents that have the indexed field, EVEN IF the index field contains a null value.
            The index skips over any document that is missing the indexed field.
            The index is "sparse" because it does not include all documents of a collection.
            By contrast, non-sparse indexes contain ALL documents in a collection, storing null values for those documents that do not contain the indexed field.
            '''
            collection = db['sparse.scores']
            collection.drop()
            collection.insert_many([
                {'userid': "newbie"},
                {'userid': "abby", 'score': 82},
                {'userid': "nina", 'score': 90},
            ])
            ###
            index_name = collection.create_index([('score', pymongo.ASCENDING)], sparse=True)
            documents = list(collection.find({'score': {'$lt': 90}}))            # user sparse index
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]['userid'], 'abby')

            # If a sparse index would result in an incomplete result set for queries and sort operations,
            # MongoDB will not use that index unless a hint() explicitly specifies the index.
            self.assertEqual(collection.count_documents({}), 3)
            self.assertEqual(collection.count_documents({}, hint=[('score', pymongo.ASCENDING)]), 2)


            collection.drop_index(index_name)
            collection.create_index([('score', pymongo.ASCENDING)], sparse=True, unique=True)
            collection.insert_one({'userid': 'mina'})  # ok
            collection.insert_one({'userid': 'netty', 'score': 12})  # ok
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                collection.insert_one({'userid': 'apache', 'score': 82})























if __name__ == '__main__':
    unittest.main(verbosity=2)