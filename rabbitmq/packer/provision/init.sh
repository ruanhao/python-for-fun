#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:


curl -s https://packagecloud.io/install/repositories/rabbitmq/erlang/script.rpm.sh | sudo bash
sudo yum install -y erlang socat logrotate

wget https://github.com/rabbitmq/rabbitmq-server/releases/download/v3.7.9/rabbitmq-server-3.7.9-1.el7.noarch.rpm
sudo rpm --import https://www.rabbitmq.com/rabbitmq-signing-key-public.asc
sudo rpm -Uvh rabbitmq-server-3.7.9-1.el7.noarch.rpm

sudo chown -R rabbitmq:rabbitmq /var/lib/rabbitmq/
sudo systemctl start rabbitmq-server
echo "mycookie" | sudo tee /var/lib/rabbitmq/.erlang.cookie
sudo systemctl stop rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
