#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns



# 创建 deployment
kubectl create -f $_SCRIPT_DIR/kubia-deployment-v1.yaml --record
kubectl rollout status deployment kubia || true # wait for: deployment "kubia" successfully rolled out
num_of_kubia_rs=$( kubectl get rs | grep kubia | wc -l )
[[ "$num_of_kubia_rs" == 1 ]] || fail "There must be only one replicaset for kubia"

# 创建 service
kubectl create -f $_SCRIPT_DIR/kubia-svc-nodeport.yaml
nodeport=$( kubectl get svc kubia-nodeport --output jsonpath='{.spec.ports[*].nodePort}' )
info "node port: $nodeport"
sleep 1
curl -s 172.42.42.100:$nodeport | grep v1

kubectl patch deployment kubia -p '{"spec": {"minReadySeconds": 10}}' # 减慢些升级速度
# 触发升级
info "Updating image ..."
kubectl set image deployment kubia nodejs=luksa/kubia:v2
kubectl rollout status deployment kubia || true
num_of_kubia_rs=$( kubectl get rs | grep kubia | wc -l )
[[ "$num_of_kubia_rs" == 2 ]] || fail "There must be 2 replicaset for kubia"
curl -s 172.42.42.100:$nodeport | grep v2

# 查看升级历史
kubectl rollout history deployment kubia

# 回退
kubectl rollout undo deployment kubia --to-revision=1
kubectl rollout status deployment kubia || true
curl -s 172.42.42.100:$nodeport | grep v1