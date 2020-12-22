#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns

# 先删除 node 上的标签
kubectl label node worker2 disk-
# 创建带有 nodeSelector 的 DaemonSet
kubectl create -f $_SCRIPT_DIR/ssd-monitor-daemonset.yaml
kubectl get ds
kubectl get ds | grep ssd-monitor | grep -q -E '0.*0.*0.*0.*0' || fail "No pod should be scheduled because no node matches the label"
kubectl label node worker2 disk=ssd
wait_for_pod_ready_by_label app=ssd-monitor
kubectl get ds
kubectl get ds | grep 'ssd-monitor' | grep -E '1.*1.*1.*1.*1'
