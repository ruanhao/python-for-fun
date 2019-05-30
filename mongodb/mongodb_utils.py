#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import pymongo
import time
import uuid
from pymongo import MongoClient


def get_client(host='localhost', port=27017):
    return MongoClient(host, port)

def new_collection(db, cname):
    c = db[cname]
    c.drop()
    return c

def timeit(callable):
    begin = time.time()
    callable()
    end = time.time()
    return end - begin





def random_str(len=5):
    return str(uuid.uuid4()).replace('-', '')[:len]
