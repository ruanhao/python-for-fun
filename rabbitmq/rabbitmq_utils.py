#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import rabbitpy
import datetime

def properties(content_type='application/json'):
    return {
        'content_type': content_type,
        'timestamp': datetime.datetime.now(),
    }

def declare_exchange(channel, name, **kw_args):
    exchange = rabbitpy.Exchange(channel, name, **kw_args)
    exchange.declare()
    return exchange

def declare_queue(channel, name):
    queue = rabbitpy.Queue(channel, name)
    queue.declare()
    return queue

def bind(queue, exchange, routing_key):
    queue.bind(exchange, routing_key)
