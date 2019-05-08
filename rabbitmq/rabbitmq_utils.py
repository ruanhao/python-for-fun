#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import rabbitpy
import datetime
import requests
import time

def properties(content_type='application/json'):
    return {
        'content_type': content_type,
        'timestamp': datetime.datetime.now(),
    }

def declare_exchange(channel, name, **kw_args):
    exchange = rabbitpy.Exchange(channel, name, **kw_args)
    exchange.declare()
    return exchange

def declare_queue(channel, name, **kw_args):
    queue = rabbitpy.Queue(channel, name, **kw_args)
    queue.declare()
    return queue

def bind(queue, exchange, routing_key):
    queue.bind(exchange, routing_key)


def get_channel(url):
    return rabbitpy.Connection(url).channel()

def get_unacked_number(queue_name):
    time.sleep(10)               # wait for refresh
    return requests.get(f'http://localhost:15672/api/queues/%2f/{queue_name}',
                        auth=('guest', 'guest')).json()['messages_unacknowledged']
