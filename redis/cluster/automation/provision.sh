#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:


### Install Redis

cp /vagrant/redis_`hostname`.conf /etc/redis/6379.conf
service redis-server restart

cat <<EOF | sudo -u vagrant tee /home/vagrant/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF


echo 192.168.33.11 master1 >> /etc/hosts
echo 192.168.33.12 master2 >> /etc/hosts
echo 192.168.33.13 master3 >> /etc/hosts
echo 192.168.33.14 master4 >> /etc/hosts

echo 192.168.33.21 slave1 >> /etc/hosts
echo 192.168.33.22 slave2 >> /etc/hosts
echo 192.168.33.23 slave3 >> /etc/hosts
echo 192.168.33.24 slave4 >> /etc/hosts
