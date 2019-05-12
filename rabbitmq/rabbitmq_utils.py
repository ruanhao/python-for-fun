#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import rabbitpy
import datetime
import requests
import time
import pika
import subprocess
import sys

def key_find(lst, key, value):
    return next((item for item in lst if item[key] == value), None)

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

def get_all_queues():
    return requests.get(f'http://localhost:15672/api/queues/', auth=('guest', 'guest')).json()

def all_queues():
    return get_all_queues()



def pika_connection(host='localhost'):
    return pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

def pika_channel(host='localhost'):
    return pika_connection(host).channel()

def pika_queue_purge(channel, queue):
    if isinstance(queue, list):
        for q in queue:
            channel.queue_purge(q)
    else:
        channel.queue_purge(queue)


def pika_queue_declare(channel, queue_name, **kw_args):
    queue_declare_ok_method = channel.queue_declare(queue_name, **kw_args).method
    queue = queue_declare_ok_method.queue
    channel.queue_purge(queue)
    return queue

def pika_exchange_declare(channel, exchange_name, **kwargs):
    exchange_declare_ok_method = channel.exchange_declare(exchange_name, **kwargs).method
    return exchange_name


def pika_consume(channel, queue_name, on_msg_cb, **kwargs):
    consumer_tag = channel.basic_consume(queue_name, on_msg_cb, **kwargs)
    return consumer_tag


def pika_simple_callback(channel, method, properties, body):
    # channel: pika.Channel
    # method: pika.spec.Basic.Deliver
    # properties: pika.spec.BasicProperties
    # body: bytes
    print(f'Msg received on channel ({channel}):\nMethod: {method}\nProperties: {properties}\nBody: {body}')

def pika_queue_counters(channel, queue):
    '''
    Using a passive queue declare, you can poll for the presence of the queue and act when you either see there are messages pending or
    when the queue no longer exists.
    '''
    time.sleep(0.5)
    try:
        method = channel.queue_declare(queue, passive=True).method
        return (method.consumer_count, method.message_count)
    except pika.exceptions.ChannelClosedByBroker as e:
        if e.reply_code == 404:
            return None
        raise e

def pika_simple_publish(channel, exchange, rk, body):
    channel.basic_publish(exchange=exchange,
                          routing_key=rk,
                          properties=pika.BasicProperties(
                              timestamp=int(datetime.datetime.now().timestamp()),
                              content_encoding='utf-8',
                          ),
                          body=body)

def pika_queue_bind(channel, queue, exchange, routing_key=None, **kwargs):
    channel.queue_bind(queue, exchange, routing_key, **kwargs)

def pika_exchange_bind(channel, dest, src, rk='', **kwargs):
    channel.exchange_bind(dest, src, rk, **kwargs)


def utf8(encoded):
    return encoded.decode('utf-8')

def pika_basic_get(channel, queue):
    method_frame, _header_frame, body = channel.basic_get(queue)
    if method_frame:
        decoded = utf8(body)
        channel.basic_ack(method_frame.delivery_tag)
        return decoded
    else:
        return None

def run(script, quiet=False):
    if quiet is False:
        print(f"====== {script} ======")
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate(timeout=60)
    stdout_str = stdout.decode('utf-8').rstrip('\n')
    stderr_str = stderr.decode('utf-8').rstrip('\n')
    if quiet is False:
        print(f'{stdout_str}')
        print(f'{stderr_str}', file=sys.stderr)
        if proc.returncode:
            raise Exception('Exit Code: %s' % proc.returncode)
    return stdout_str