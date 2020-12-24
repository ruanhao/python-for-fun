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

status=$(vagrant ssh gluster-server-1 -- 'sudo gluster peer status')
if echo $status | grep -q 'Number of Peers: 0'; then
    info "Probing for peers ..."
    vagrant ssh gluster-server-1 -- 'sudo gluster peer probe 172.21.12.12 ; sudo gluster peer probe 172.21.12.13'

fi

volume_name="myvolume-$(date +%s)"

info "Creating volume [$volume_name] ..."
vagrant ssh gluster-server-1 -- sudo gluster volume create $volume_name replica 3 transport tcp 172.21.12.11:/brick 172.21.12.12:/brick 172.21.12.13:/brick force
info "Starting volume [$volume_name] ..."
vagrant ssh gluster-server-1 -- sudo gluster volume start $volume_name

info "Mounting the volume ..."
vagrant ssh gluster-client -- "sudo mkdir /mnt/$volume_name && sudo mount -t glusterfs 172.21.12.11:/$volume_name /mnt/$volume_name"

info "Show peer status"
vagrant ssh gluster-server-1 -- sudo gluster peer status
info "Show volume info"
vagrant ssh gluster-server-1 -- sudo gluster volume info