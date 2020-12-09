#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

. _common.sh

bash _cleanup.sh


# STEP 1: handshake
info "[Meeting] master1 => master2 ..."
vagrant ssh master1 -- redis-cli cluster meet 192.168.33.12 6379 # master2
info "[Meeting] master1 => master3 ..."
vagrant ssh master1 -- redis-cli cluster meet 192.168.33.13 6379 # master3
info "[Meeting] master1 => slave1 ..."
vagrant ssh master1 -- redis-cli cluster meet 192.168.33.21 6379 # master3
info "[Meeting] master1 => slave2 ..."
vagrant ssh master1 -- redis-cli cluster meet 192.168.33.22 6379 # master3
info "[Meeting] master1 => slave3 ..."
vagrant ssh master1 -- redis-cli cluster meet 192.168.33.23 6379 # master3

python3 -m unittest steps_test.UnitTest.test_AFTER_MEET

# STEP 2: allocate slots
info "[Adding slots] master1 ..."
vagrant ssh master1 -- redis-cli cluster addslots {0..5461}
info "[Adding slots] master2 ..."
vagrant ssh master2 -- redis-cli cluster addslots {5462..10922}
info "[Adding slots] master3 ..."
vagrant ssh master3 -- redis-cli cluster addslots {10923..16383}
sleep 10                         # wait a while
python3 -m unittest steps_test.UnitTest.test_AFTER_ADDSLOTS


# STEP 3: slave of
master1_node_id=$( vagrant ssh master1 -- redis-cli cluster myid )
master2_node_id=$( vagrant ssh master2 -- redis-cli cluster myid )
master3_node_id=$( vagrant ssh master3 -- redis-cli cluster myid )
info "[Replicate] slave1 -> master1 ($master1_node_id)"
vagrant ssh slave1 -- redis-cli cluster replicate $master1_node_id
info "[Replicate] slave2 -> master1 ($master2_node_id)"
vagrant ssh slave2 -- redis-cli cluster replicate $master2_node_id
info "[Replicate] slave3 -> master1 ($master3_node_id)"
vagrant ssh slave3 -- redis-cli cluster replicate $master3_node_id
sleep 10
python3 -m unittest steps_test.UnitTest.test_AFTER_REPLICATE