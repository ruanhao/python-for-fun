#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

function info() {
    echo -e $(date +"%T") - "\033[0;32m$@\033[0m"
}

function alert() {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
}

function fail() {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
    exit 1
}

function wait_for_pod_ready_by_name {
    info "Waiting for pod $1 to be ready ..."
    kubectl wait --for=condition=ready pod/$1 --timeout=180s
}

function wait_for_pod_ready_by_label {
    local labels=$@
    info "Waiting for pods ($labels) to be ready ..."
    kubectl wait --for=condition=ready pod -l $labels --timeout=180s
}

function new_ns {
    if [[ -n "$1" ]]; then
        nns=${1}-$(date +%s)
    else
        filename=`basename "$0"`
        filename=$(basename -- "$filename"|tr '_' '-')
        filename=${filename,,}
        filename="${filename%.*}"
        nns=${filename}-$(date +%s)
    fi
    kubectl create namespace $nns
    info "New namespace $nns created"
    kubectl config set-context $(kubectl config current-context) --namespace $nns >/dev/null

}

function default_ns {
    kubectl config set-context $(kubectl config current-context) --namespace default
}



export -f new_ns
export -f default_ns
export -f info
export -f alert
export -f fail
export -f wait_for_pod_ready_by_name
export -f wait_for_pod_ready_by_label