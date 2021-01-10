#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

for f in /proc/sys/net/ipv4/conf/*; do
    if [[ "$f" == *default ]]; then
        continue
    fi
    echo 0 > $f/arp_ignore
    echo 0 > $f/arp_announce
    echo 1 > $f/rp_filter
done

ip neigh flush all