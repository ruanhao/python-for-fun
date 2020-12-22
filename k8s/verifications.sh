#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: Run this script as
# vagrant ssh master -- bash /vagrant/verifications.sh

set -e

_SCRIPT_DIR=$(cd $(dirname $0); pwd)

source $_SCRIPT_DIR/_common.sh


function test_pod {
    info "=========== Pod cases ==========="
    bash -e $_SCRIPT_DIR/pod/test_pod_create.sh
}

function test_daemonset {
    info "=========== Daemonset cases ==========="
    bash -e $_SCRIPT_DIR/daemonset/test_daemonset_with_nodeSelector.sh
}

function test_service {
    info "=========== Service cases ==========="
    bash -e $_SCRIPT_DIR/service/test_nodePort.sh
}

function test_deployment {
    info "=========== Deployment cases ==========="
    bash -e $_SCRIPT_DIR/deployment/test_rolling_upgrade.sh
}

function test_statefulset {
    info "=========== Statefulset cases ==========="
    bash -e $_SCRIPT_DIR/statefulset/test_statefulset.sh
    bash -e $_SCRIPT_DIR/statefulset/test_statefulset_with_storageclass.sh
}

test_pod
test_daemonset
test_service
test_deployment
test_statefulset


info "SUCCESS"