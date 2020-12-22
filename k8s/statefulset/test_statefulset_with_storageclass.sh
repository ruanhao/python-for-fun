#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:


set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns



kubectl create -f $_SCRIPT_DIR/kubia-statefulset-sc-glusterfs.yaml
info "Show sts"
kubectl get sts
wait_for_pod_ready_by_name kubia-0
wait_for_pod_ready_by_name kubia-1

timestamp=$( date +%s )
info "timestamp: $timestamp"
kubectl exec -i kubia-0 -- bash -c "echo $timestamp > /var/data/timestamp"
kubectl delete pod kubia-0
sleep 1
wait_for_pod_ready_by_name kubia-0
kubectl exec -i kubia-0 -- cat /var/data/timestamp
timestamp0=$( kubectl exec -i kubia-0 -- cat /var/data/timestamp )
[[ "$timestamp0" == "$timestamp" ]] || fail "Data should be persistent after pod recreating"