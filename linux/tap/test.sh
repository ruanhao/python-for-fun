#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: bash test.sh

set -e


info () {
    echo -e $(date +"%T") - "\033[0;32m$@\033[0m"
}

alert () {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
}

fail() {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
    exit 1
}


vagrant ssh client -- sudo systemctl start socat-tap-client
vagrant ssh client -- ping server -c 1 -W 3
vagrant ssh client -- sudo systemctl stop socat-tap-client
vagrant ssh client -- "ping server -c 1 -W 3" && fail "Tunnel is down. Ping should be failed"
vagrant ssh client -- sudo systemctl start socat-tap-client
vagrant ssh client -- ping server -c 1 -W 3

info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
