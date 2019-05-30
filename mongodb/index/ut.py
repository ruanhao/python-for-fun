#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import unittest
import datetime
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


        with self.subTest("Create a Compound Index"):
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

        with self.subTest("Sort Order"):
            collection = new_collection(db, 'events')
            collection.insert_many([
                {
                    'username': random_str(3),
                    'date': datetime.datetime.now(),
                    'score': random.randint(0, 100),
                }
            for _ in range(1000000)])
            ###
            collection.create_index([('username', pymongo.ASCENDING), ('date', pymongo.DESCENDING)])
            t1 = timeit(lambda: collection.find({}, sort=[('username', pymongo.ASCENDING), ('date', pymongo.DESCENDING)]))
            t2 = timeit(lambda: collection.find({}, sort=[('username', pymongo.DESCENDING), ('date', pymongo.ASCENDING)]))
            t3 = timeit(lambda: collection.find({}, sort=[('username', pymongo.ASCENDING), ('date', pymongo.ASCENDING)]))
            t4 = timeit(lambda: collection.find({}, sort=[('score', pymongo.ASCENDING)]))
            print(f't1: {t1}, t2: {t2}, t3: {t3}, t4: {t4}')

            # for d in collection.find({}, sort=[('username', pymongo.ASCENDING), ('date', pymongo.DESCENDING)], limit=10):
            #     pprint(d)










if __name__ == '__main__':
    unittest.main(verbosity=2)