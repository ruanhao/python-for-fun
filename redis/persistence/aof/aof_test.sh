#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: v ssh < test.sh

set -e
set -x

function start_redis_server {
    sudo service redis-server start
    sleep 1
}

function restart_redis_server {
    sudo service redis-server restart
    sleep 1
}

function stop_redis_server {
    sudo service redis-server stop
    sleep 1
}


stop_redis_server
sudo rm -rf /var/redis/*.aof

start_redis_server
[[ -e /var/redis/appendonly.aof ]] || exit 1 # 一启动即生成 aof 文件
redis-cli dbsize | grep 0       # 确保全新的环境
redis-cli set k1 v1
redis-cli set k2 v2
stop_redis_server
echo "hello world" | sudo -u redis tee -a /var/redis/appendonly.aof # 破坏 aof 文件

start_redis_server
ss -ant state listening | grep 6379 && exit 1 || true # aof 损坏，无法启动
yes | sudo -u redis redis-check-aof --fix /var/redis/appendonly.aof # 修复 aof 文件
restart_redis_server

redis-cli dbsize | grep 2
redis-cli get k1 | grep v1

cowsay SUCCEED
