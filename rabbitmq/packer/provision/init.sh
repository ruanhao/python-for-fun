#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

version=3.7.14

curl -s https://packagecloud.io/install/repositories/rabbitmq/erlang/script.rpm.sh | sudo bash
sudo yum install -y erlang socat logrotate

wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v$version/rabbitmq-server-$version-1.el7.noarch.rpm
sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
sudo rpm -Uvh rabbitmq-server-$version-1.el7.noarch.rpm

sudo chown -R rabbitmq:rabbitmq /var/lib/rabbitmq/
sudo systemctl start rabbitmq-server
echo "mycookie" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo sed -i 's/{loopback_users, \[<<"guest">>\]},/{loopback_users, []},/1' /usr/lib/rabbitmq/lib/rabbitmq_server-*/ebin/rabbit.app
sudo systemctl stop rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
