#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns


# 创建基于 hostPath 的 pv
timestamp=$( date +%s )
info "timestamp: $timestamp"
cat <<EOF | kubectl create -f -
kind: List
apiVersion: v1
items:
- apiVersion: v1
  kind: PersistentVolume
  metadata:
    name: pv-a-$timestamp
  spec:
    capacity:
      storage: 1Mi
    accessModes:
      - ReadWriteOnce
    persistentVolumeReclaimPolicy: Recycle
    hostPath:
      path: /tmp/pv-a-$timestamp
- apiVersion: v1
  kind: PersistentVolume
  metadata:
    name: pv-b-$timestamp
  spec:
    capacity:
      storage: 1Mi
    accessModes:
      - ReadWriteOnce
    persistentVolumeReclaimPolicy: Recycle
    hostPath:
      path: /tmp/pv-b-$timestamp
- apiVersion: v1
  kind: PersistentVolume
  metadata:
    name: pv-c-$timestamp
  spec:
    capacity:
      storage: 1Mi
    accessModes:
      - ReadWriteOnce
    persistentVolumeReclaimPolicy: Recycle
    hostPath:
      path: /tmp/pv-c-$timestamp

EOF
kubectl create -f $_SCRIPT_DIR/kubia-statefulset-sc-empty.yaml
wait_for_pod_ready_by_name kubia-0
wait_for_pod_ready_by_name kubia-1
info "Show all pvc"
kubectl get pvc
info "Show all pv"
kubectl get pv
kubectl exec -i kubia-0 -- bash -c "echo $timestamp > /var/data/timestamp"
kubectl delete pod kubia-0
sleep 1
wait_for_pod_ready_by_name kubia-0
kubectl exec -i kubia-0 -- cat /var/data/timestamp
timestamp0=$( kubectl exec -i kubia-0 -- cat /var/data/timestamp )
[[ "$timestamp0" == "$timestamp" ]] || fail "Data should be persistent after pod recreating"