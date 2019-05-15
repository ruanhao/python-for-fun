#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
import threading
import datetime
import time
import unittest
import rabbitpy
import random
from rabbitmq_utils import *



def init_env():
    run('docker stop `docker ps --format="{{.Names}}" | grep rabbit`', True)
    run('docker run --rm -d --hostname rabbit --name rabbit -e RABBITMQ_PID_FILE=/var/lib/rabbitmq/rabbit.pid -p 15672:15672 -p 5672:5672 rabbitmq:3-management', True)
    run('docker exec rabbit rabbitmqctl wait /var/lib/rabbitmq/rabbit.pid', True)


def _run(cmd, quiet=False):
    return run(f"docker exec rabbit {cmd}", quiet)



class UnitTest(unittest.TestCase):

    def setUp(self):
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")


    def test_vhost_management(self):
        init_env()
        new_vhost = get_uuid()
        _run(f'rabbitmqctl add_vhost {new_vhost}')
        stdout = _run('rabbitmqctl list_vhosts')
        self.assertIn(new_vhost, stdout)


    def test_permissions_management(self):
        '''
        RabbitMQ 中的授予权限是指在 vhost 级别对用户而言的权限授予
        rabbitmqctl set permissions [-p vhost] {user) {conf) {write) {read)
        vhost: 授予用户访问权限的 vhost名称，默认为 /
        user: 可以访问指定 vhost 的用户名
        conf: 匹配用户在哪些资源上拥有可配置权限的正则表达式
        write: 匹配用户在哪些资源上拥有可写权限的正则表达式
        read: 匹配用户在哪些资源上拥有可读权限的正则表达式

        - 可配置指的是队列和交换器的创建及删除之类的操作
        - 可写指的是发布消息
        - 可读指与消息有关的操作，包括读取消息及清空整个队列等
        '''
        init_env()
        channel = pika_channel()
        ###
        # 在以 "queue" 开头的资源上具备可配置权限， 并在所有资源上拥有可写、可读权限
        _run('rabbitmqctl set_permissions guest "^queue-.*" ".*" ".*"')
        _run('rabbitmqctl list_permissions | column -t')
        _run('rabbitmqctl list_user_permissions guest | column -t')
        pika_queue_declare(channel, f'queue-{get_uuid()}')
        with self.assertRaises(pika.exceptions.ChannelClosedByBroker) as raised_exception:
            pika_queue_declare(channel, f'{get_uuid()}-queue')
        self.assertEqual(raised_exception.exception.reply_code, 403)
        self.assertIn("ACCESS_REFUSED",raised_exception.exception.reply_text)
        self.assertTrue(channel.is_closed)
        _run('rabbitmqctl clear_permissions guest')
        _run('rabbitmqctl list_permissions | column -t')
        _run('rabbitmqctl list_user_permissions guest | column -t')


    def test_user_management(self):
        '''
        用户的角色分为 5 种类型
        - none: 无任何角色，新创建的用户的角色默认为 none
        - management: 可以访问 Web 管理页面
        - policymaker: 包含 management 的所有权限，并且可以管理策略 (Policy) 和参数 (Parameter)
        - monitoring: 包含 management 的所有权限，并且可以看到所有连接，信道及节点 相关的信息
        - administartor: （最高权限）包含 monitoring 的所有权限，井且可以管理用户，虚拟主机，权限，策略，参数等
        '''
        init_env()
        ###
        _run('rabbitmqctl add_user root p@55w0rd')
        self.assertIn('root', _run('rabbitmqctl list_users')[0])
        _run('rabbitmqctl change_password root newP@55w0rd')
        _run('rabbitmqctl authenticate_user root newP@55w0rd')
        _run('rabbitmqctl set_user_tags root monitoring,policymaker')
        _run('rabbitmqctl list_users -q')


    def test_app_management(self):
        init_env()
        ###

        # with self.subTest("rabbitmqctl stop"):
        #     '''
        #     用于停止运行 RabbitMQ 的 Erlang 虚拟机和 RabbitMQ 服务应用
        #     '''
        #     self.assertIn('running', run('docker ps --format="{{.Names}}" | grep rabbit && echo running', True)[0])
        #     _run('rabbitmqctl stop /var/lib/rabbitmq/rabbit.pid', True)
        #     time.sleep(3)
        #     self.assertEqual('stopped', run('docker ps --format="{{.Names}}" | grep rabbit || echo stopped', True)[0])
        #     init_env()

        # with self.subTest("rabbitmqctl shutdown"):
        #     '''
        #     用于停止运行 RabbitMQ 的 Erlang 虚拟机和 RabbitMQ 服务应用
        #     与 rabbitmqctl stop 不同的是，它不需要指定 pid_file
        #     '''
        #     self.assertIn('running', run('docker ps --format="{{.Names}}" | grep rabbit && echo running', True)[0])
        #     _run('rabbitmqctl shutdown', True)
        #     time.sleep(3)
        #     self.assertEqual('stopped', run('docker ps --format="{{.Names}}" | grep rabbit || echo stopped', True)[0])
        #     init_env()


        # with self.subTest('rabbitmqctl [stop/start]_app'):
        #     '''
        #     stop_app: 停止 RabbitMQ 服务应用，但是 Erlang 虚拟机还是处于运行状态
        #     '''
        #     _run('rabbitmqctl stop_app')
        #     _run('rabbitmqctl start_app')

        with self.subTest('rabbitmqctl reset'):
            '''
            将 RabbitMQ 节点重置还原到最初状态。
            包括从原来所在的集群中删除此节点，从管理数据库中删除所有的配置数据，如己配置的用户，vhost 等，以及删除所有的持久化消息。
            执行 rabbitmqctl reset 命令前必须先执行 rabbitmqctl stop_app
            '''
            pass

        with self.subTest('rabbitmqctl force_reset'):
            '''
            强制将 RabbitMQ 节点重置还原到最初状态。
            不同于 rabbitmqctl reset 命令，rabbitmqctl force reset 命令不论当前管理数据库的状态和集群配置是什么，
            都会无条件地重置节点。它只能在数据库或集群配置己损坏的情况下使用。
            执行 rabbitmqctl force_reset 命令前必须先执行 rabbitmqctl stop_app
            '''
            pass

        with self.subTest('rabbitmqctl rotate_logs {suffix}'):
            '''
            指示 RabbitMQ 节点轮换日志文件。
            RabbitMQ 节点会将原来的日志文件中的内容追加到"原始名称+后缀"的日志文件中，
            然后再将新的日志内容记录到新创建的日志中(与原日志文件同 名)。
            当目标文件不存在时，会重新创建。
            如果不指定后缀 suffix 则日志文件只是重新打开而不会进行轮换。
            '''
            pass

























if __name__ == '__main__':
    unittest.main(verbosity=2)