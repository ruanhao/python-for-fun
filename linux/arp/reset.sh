#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

for f in /proc/sys/net/ipv4/conf/*; do
    if [[ "$f" == *default ]]; then
        continue
    fi
    echo 0 > $f/arp_ignore
    echo 0 > $f/accept_local
    echo 0 > $f/arp_announce
    echo 1 > $f/rp_filter
done
if [[ -d /proc/sys/net/ipv4/conf/veth0 ]]; then
    ip link del dev veth0
fi
ip neigh flush all
iptables -t nat -F
iptables -t mangle -F
iptables -F


ip rule del table 100 2>/dev/null || true
ip rule del pref 100 2>/dev/null || true
