#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns

kubectl create -f $_SCRIPT_DIR/kubia-rc.yaml
wait_for_pod_ready_by_label app=kubia
kubectl get rc
kubectl get rc | grep -q -E '3.*3.*3' || fail "Wrong state"
kubectl create -f $_SCRIPT_DIR/kubia-svc-nodeport.yaml
kubectl get svc kubia-nodeport
nodeport=$( kubectl get svc kubia-nodeport --output jsonpath='{.spec.ports[*].nodePort}' )
info "node port: $nodeport"
curl -s 172.42.42.100:$nodeport
curl -s 172.42.42.101:$nodeport
curl -s 172.42.42.102:$nodeport