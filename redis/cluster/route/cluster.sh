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

python3 -m unittest verifications.UnitTest.test_HASHTAG
python3 -m unittest verifications.UnitTest.test_MOVED
