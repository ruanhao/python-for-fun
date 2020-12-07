#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:


### Install Redis

REDIS_VERSION=6.0.9
apt-get update
apt-get install cowsay make gcc pkg-config -y
mkdir /opt/redis
cd /opt/redis
wget http://download.redis.io/releases/redis-$REDIS_VERSION.tar.gz
tar xfvz redis-$REDIS_VERSION.tar.gz
cd redis-$REDIS_VERSION
make MALLOC=libc
make install
useradd redis
mkdir -p /etc/redis
mkdir -p /var/redis
chown redis:redis /var/redis
cp /vagrant/redis_`hostname`.conf /etc/redis/6379.conf
cp /vagrant/redis.init.d /etc/init.d/redis_6379
chmod a+x /etc/init.d/redis_6379
update-rc.d redis_6379 defaults
service redis-server start


### Customize env
cat <<EOF | sudo -u vagrant tee /home/vagrant/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF

echo 192.168.33.10 master >> /etc/hosts
echo 192.168.33.11 slave1 >> /etc/hosts
echo 192.168.33.12 slave2 >> /etc/hosts
