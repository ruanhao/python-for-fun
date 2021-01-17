#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: vagrant ssh dut -- sudo bash /vagrant/test_add_rule.sh
# http://ruanhao.cc/blog/2021-01-10-arp.html#org44dca23

set -e

info () {
    echo -e $(date +"%T") - "\033[0;32m$@\033[0m"
}

alert () {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
}

fail() {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
    exit 1
}

bash /vagrant/reset.sh

ip link add veth0 type veth peer name veth1
ip link set veth0 up
ip link set veth1 up
ip a a 192.168.1.2/24 dev veth0
ip a a 192.168.1.3/24 dev veth1

sleep 1

echo 1 > /proc/sys/net/ipv4/conf/veth1/accept_local
echo 1 > /proc/sys/net/ipv4/conf/veth0/accept_local
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/veth0/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/veth1/rp_filter

iptables -t nat -I PREROUTING ! -d 10.0.2.0/24 -j LOG --log-prefix "nat@PREROUTING: " --log-level 4
iptables -t mangle -I POSTROUTING ! -d 10.0.2.0/24 -j LOG --log-prefix "mangle@POSTROUTING: " --log-level 4
iptables -I INPUT ! -d 10.0.2.0/24 -j LOG --log-prefix "filter@INPUT: " --log-level 4
iptables -I OUTPUT ! -d 10.0.2.0/24 -j LOG --log-prefix "filter@OUTPUT: " --log-level 4

ip rule add to 192.168.1.2/32 pref 10 tab 100
ip route add 192.168.1.2/32 dev veth1 tab 100

ping -I veth0 192.168.1.3 -c 1 -W 1 && fail "Ping should be failed because of no ARP Reply being sent when veth0 receiving ARP Request"


info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!"
