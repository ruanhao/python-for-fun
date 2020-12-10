#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

. _common.sh

bash -e _reset_cluster.sh

info "Creating cluster ..."

echo yes | vagrant ssh master1 -- redis-cli --cluster create \
        192.168.33.11:6379 192.168.33.12:6379 192.168.33.13:6379 \
        192.168.33.21:6379 192.168.33.22:6379 192.168.33.23:6379 \
        --cluster-replicas 1

wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_ADDSLOTS

info "Adding one new master node ..."
vagrant ssh master1 -- redis-cli --cluster add-node 192.168.33.14:6379 192.168.33.11:6379 # 需要加入的节点 (192.168.33.14:6379) 放前面
wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_ONE_MASTER_ADDED

info "Adding new slave node ..."
master4_id=$( vagrant ssh master4 -- redis-cli cluster myid )
vagrant ssh master1 -- redis-cli --cluster add-node 192.168.33.24:6379 192.168.33.11:6379 --cluster-slave --cluster-master-id $master4_id
wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_ONE_SLAVE_ADDED
vagrant ssh master1 -- redis-cli --cluster check 192.168.33.11:6379 --cluster-search-multiple-owners # 检查集群


info "Resharding slots ..."
master1_id=$( vagrant ssh master1 -- redis-cli cluster myid )
vagrant ssh master1 -- redis-cli --cluster reshard 192.168.33.11:6379 \
        --cluster-from $master1_id --cluster-to $master4_id \
        --cluster-slots 10 --cluster-yes --cluster-timeout 5000 --cluster-pipeline 10 --cluster-replace
wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_RESHARD

info "Auto rebalancing slots ..."
vagrant ssh master1 -- redis-cli --cluster rebalance 192.168.33.11:6379 # 自动平衡
wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_AUTO_REBALANCE

info "Rebalancing slots by weight ..."
master2_id=$( vagrant ssh master2 -- redis-cli cluster myid )
master3_id=$( vagrant ssh master3 -- redis-cli cluster myid )
vagrant ssh master1 -- redis-cli --cluster rebalance --cluster-weight ${master1_id}=4 ${master2_id}=3 ${master3_id}=2 ${master4_id}=1 192.168.33.11:6379 # 权重平衡
wait_a_while 5
python3 -m unittest verifications.UnitTest.test_AFTER_WEIGHTED_REBALANCE

info "Try deleting a master node with slots ..."
vagrant ssh master1 -- redis-cli --cluster del-node 192.168.33.11:6379 $master4_id && alert "master node with slots should not be deleted successfully" || true

info "Shrinking cluster ..."
slave4_id=$( vagrant ssh slave4 -- redis-cli cluster myid )
vagrant ssh master1 -- redis-cli --cluster del-node 192.168.33.11:6379 $slave4_id
wait_a_while 3
python3 -m unittest verifications.UnitTest.test_AFTER_SLAVE4_DELETED
info "Moving all slots in master4 to other node ..."
vagrant ssh master1 -- redis-cli --cluster rebalance --cluster-weight ${master1_id}=4 ${master2_id}=3 ${master3_id}=3 ${master4_id}=0 192.168.33.11:6379
wait_a_while 3
python3 -m unittest verifications.UnitTest.test_AFTER_MOVE_ALL_SLOTS_IN_MASTER4
info "Try deleting a master node without slots ..."
vagrant ssh master1 -- redis-cli --cluster del-node 192.168.33.11:6379 $master4_id
wait_a_while 3
python3 -m unittest verifications.UnitTest.test_AFTER_MASTER4_DELETED
