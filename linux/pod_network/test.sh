#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: bash test.sh

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

host1_eth1_mac=$( vagrant ssh host1 -- cat /sys/class/net/eth1/address )
host1_br0_mac=$( vagrant ssh host1 -- cat /sys/class/net/br0/address )
[[ "$host1_eth1_mac" == "$host1_br0_mac" ]] || fail "Bridge mac should be the same as physical mac (host1)"

host2_eth1_mac=$( vagrant ssh host2 -- cat /sys/class/net/eth1/address )
host2_br0_mac=$( vagrant ssh host2 -- cat /sys/class/net/br0/address )
[[ "$host2_eth1_mac" == "$host2_br0_mac" ]] || fail "Bridge mac should be the same as physical mac (host2)"

vagrant ssh host1 -- '/sbin/ip route get 10.10.103.92 | grep -q "dev br0"' || fail "10.10.103.0/24 should go through bridge (host1)"
vagrant ssh host1 -- '/sbin/ip route get 172.17.2.1 | grep -q "via 10.10.103.92 dev br0"' || fail "172.17.2.0/24 should go via 10.10.103.92 through bridge (host1)"
vagrant ssh host1 -- '/sbin/ip route get 172.17.1.1 | grep -q "dev br0"' || fail "172.17.1.0/24 should go through bridge (host1)"

pod_1_routes=$( vagrant ssh host1 -- sudo /sbin/ip netns exec pod-1 /sbin/ip route )
echo $pod_1_routes | grep -q "172.17.1.0/24 dev eth0" || fail "172.17.1.0/24 should go through eth0 (pod-1)"
echo $pod_1_routes | grep -q "10.10.103.91 dev eth0" || fail "Host IP should go directly through eth0 (pod-1)"
echo $pod_1_routes | grep -q "default via 10.10.103.91 dev eth0" || fail "Wrong default GW (pod-1)"

vagrant ssh host2 -- '/sbin/ip route get 10.10.103.91 | grep -q "dev br0"' || fail "10.10.103.0/24 should go through bridge (host2)"
vagrant ssh host2 -- '/sbin/ip route get 172.17.1.1 | grep -q "via 10.10.103.91 dev br0"' || fail "172.17.1.0/24 should go via 10.10.103.91 through bridge (host2)"
vagrant ssh host2 -- '/sbin/ip route get 172.17.2.1 | grep -q "dev br0"' || fail "172.17.2.0/24 should go through bridge (host2)"

# Test connectivity

vagrant ssh host1 -- sudo ip netns exec pod-1 ping -c 1 10.10.103.91 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-1 ping -c 1 10.10.103.92 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-1 ping -c 1 172.17.1.2 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-1 ping -c 1 172.17.2.3 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-1 ping -c 1 172.17.2.4 -W 3

vagrant ssh host1 -- sudo ip netns exec pod-2 ping -c 1 10.10.103.91 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-2 ping -c 1 10.10.103.92 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-2 ping -c 1 172.17.1.1 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-2 ping -c 1 172.17.2.3 -W 3
vagrant ssh host1 -- sudo ip netns exec pod-2 ping -c 1 172.17.2.4 -W 3


vagrant ssh host2 -- sudo ip netns exec pod-3 ping -c 1 10.10.103.91 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-3 ping -c 1 10.10.103.92 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-3 ping -c 1 172.17.1.1 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-3 ping -c 1 172.17.1.2 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-3 ping -c 1 172.17.2.4 -W 3

vagrant ssh host2 -- sudo ip netns exec pod-4 ping -c 1 10.10.103.91 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-4 ping -c 1 10.10.103.92 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-4 ping -c 1 172.17.1.1 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-4 ping -c 1 172.17.1.2 -W 3
vagrant ssh host2 -- sudo ip netns exec pod-4 ping -c 1 172.17.2.3 -W 3


info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
