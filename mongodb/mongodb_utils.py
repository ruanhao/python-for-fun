#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import pymongo
import time
import uuid
import subprocess
import sys
from pymongo import MongoClient


def run(script, quiet=False, timeout=60, translation=None):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=timeout)
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if translation is not None:
        stdout_str = translate(stdout_str, translation)
        stderr_str = translate(stderr_str, translation)
    if quiet is False:
        if stdout_str.strip():
            print(f'{stdout_str}')
        if stderr_str.strip():
            print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            e = Exception(stderr_str)
            e.err_code = proc.returncode
            e.err_msg = stderr_str
            raise e
    return stdout_str, stderr_str


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
