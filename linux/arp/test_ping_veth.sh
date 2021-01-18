#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: vagrant ssh dut -- sudo bash /vagrant/test_ping_veth.sh
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
ip l set lo down

echo 1 > /proc/sys/net/ipv4/conf/veth1/accept_local
echo 1 > /proc/sys/net/ipv4/conf/veth0/accept_local
echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/veth0/rp_filter
echo 0 > /proc/sys/net/ipv4/conf/veth1/rp_filter

iptables -t nat -I PREROUTING ! -d 10.0.2.0/24 -j LOG --log-prefix "nat@PREROUTING: " --log-level 4
iptables -t mangle -I POSTROUTING ! -d 10.0.2.0/24 -j LOG --log-prefix "mangle@POSTROUTING: " --log-level 4
iptables -I INPUT ! -d 10.0.2.0/24 -j LOG --log-prefix "filter@INPUT: " --log-level 4
iptables -I OUTPUT ! -d 10.0.2.0/24 -j LOG --log-prefix "filter@OUTPUT: " --log-level 4

ip rule add prio 1000 table local
ip rule del prio 0
ip rule add fwmark 100 pref 10 tab 100
ip route add 192.168.1.2/32 dev veth1 tab 100
ip route add 192.168.1.3/32 dev veth0 tab 100
iptables -t mangle -A OUTPUT -d 192.168.1.0/24 -j MARK --set-mark 100

ping -I veth0 192.168.1.3 -c 1 -W 1 || fail "Everything should be fine"

# 测试内核参数
echo 0 > /proc/sys/net/ipv4/conf/veth1/accept_local
ping -I veth0 192.168.1.3 -c 1 -W 1 && fail "veth1 will not accept packet from address on local host"
echo 1 > /proc/sys/net/ipv4/conf/veth1/accept_local # 还原

echo 1 > /proc/sys/net/ipv4/conf/veth1/rp_filter
ping -I veth0 192.168.1.3 -c 1 -W 1 && fail "Should be denied by rp_filter: in=veth1 out=lo(initial routing decision)"
echo 0 > /proc/sys/net/ipv4/conf/veth1/rp_filter # 还原

ping -I veth0 192.168.1.3 -c 1 -W 1 || fail "Everything should be fine"



info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!"
