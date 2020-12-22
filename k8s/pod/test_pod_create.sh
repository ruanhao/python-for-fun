#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

new_ns

kubectl create -f $_SCRIPT_DIR/kubia-manual.yaml
wait_for_pod_ready_by_name kubia-manual
kubectl get pod -o wide
kubectl get pod | grep kubia-manual | grep -q Running || fail "Pod [kubia-manual] is not running"
