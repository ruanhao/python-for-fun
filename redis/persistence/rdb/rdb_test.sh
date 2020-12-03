#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: v ssh < rdb_test.sh

set -e
set -x

function start_redis_server {
    sudo service redis-server start
    sleep 1
}

function stop_redis_server {
    sudo service redis-server stop
    sleep 1
}


stop_redis_server
sudo rm -rf /var/redis/dump.rdb

start_redis_server
redis-cli dbsize | grep 0       # 确保全新的环境
redis-cli set k1 v1
redis-cli set k2 v2
stop_redis_server
sudo -u redis cp /var/redis/dump.rdb /var/redis/dump.rdb.bak # 备份 dump 文件
sudo -u redis rm -rf /var/redis/dump.rdb
start_redis_server
redis-cli dbsize | grep 0

stop_redis_server
sudo -u redis rm -rf /var/redis/dump.rdb
sudo -u redis mv /var/redis/dump.rdb.bak /var/redis/dump.rdb # 还原 dump 文件
start_redis_server
redis-cli dbsize | grep 2
redis-cli get k1 | grep v1

echo "SUCCEED"
