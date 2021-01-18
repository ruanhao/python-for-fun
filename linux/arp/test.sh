#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

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


reset() {
    vagrant ssh client -- sudo bash /vagrant/reset.sh
    vagrant ssh dut -- sudo bash /vagrant/reset.sh
}

function test_arp_ignore_0 {
    reset
    vagrant ssh client -- ping 10.80.68.58 -c 1 || fail "It should be no problem when arp_ignore=0"
}

function test_arp_ignore_1 {
    reset
    # /proc/sys/net/ipv4/conf/all/arp_ignore 默认为 0 ，所以只设置 eth2/arp_ignore 即可（选两者中最大值）
    vagrant ssh dut -- 'sudo bash -c "echo 1 > /proc/sys/net/ipv4/conf/eth2/arp_ignore"'
    if vagrant ssh client -- ping 10.80.68.58 -c 1 -W 3; then
        fail "There is no ARP reply when arp_ignore=1"
    fi
}

function test_arp_announce_0 {
    reset
    vagrant ssh client -- 'sudo bash -c "echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter && echo 0 > /proc/sys/net/ipv4/conf/eth1/rp_filter"'
    vagrant ssh dut -- 'sudo bash -c "echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter && echo 0 > /proc/sys/net/ipv4/conf/eth2/rp_filter"'
    # Request who-has 10.80.68.58 tell 172.168.1.2
    vagrant ssh client -- ping -I 172.168.1.2 10.80.68.58 -c 1 -W 3 || fail "It should be ok"
}


function test_arp_announce_2 {
    reset
    vagrant ssh client -- 'sudo bash -c "echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter && echo 0 > /proc/sys/net/ipv4/conf/eth1/rp_filter"'
    vagrant ssh dut -- 'sudo bash -c "echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter && echo 0 > /proc/sys/net/ipv4/conf/eth2/rp_filter"'
    vagrant ssh client -- 'sudo bash -c "echo 2 > /proc/sys/net/ipv4/conf/all/arp_announce && echo 2 > /proc/sys/net/ipv4/conf/eth2/arp_announce"'
    # Request who-has 10.80.68.58 tell 10.80.68.10
    vagrant ssh client -- ping -I 172.168.1.2 10.80.68.58 -c 1 -W 3 || fail "It should be ok"
}





test_arp_ignore_0
test_arp_ignore_1
test_arp_announce_0
test_arp_announce_2


info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
