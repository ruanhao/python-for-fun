#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

sudo yum install git -y
sudo pip install git+https://github.com/shadowsocks/shadowsocks.git@master
cat <<EOF | sudo tee /etc/shadowsocks.json
{
    "server":"0.0.0.0",
    "server_port":40839,
    "local_port":1080,
    "password":"justfortest",
    "timeout":600,
    "method":"aes-256-cfb"
}
EOF

echo 'sudo ssserver -c /etc/shadowsocks.json -d start' | sudo tee -a /etc/rc.local
sudo chmod +x /etc/rc.d/rc.local
