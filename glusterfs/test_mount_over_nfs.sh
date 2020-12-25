#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
#

set -e

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


TERM=$RANDOM

source=/$TERM

vagrant ssh gluster-server-1 -- sudo mkdir $source
echo $TERM | vagrant ssh gluster-server-1 -- "cat | sudo tee $source/term"

info "Preparing nfs conf on server ..."
ganesha_conf=/etc/ganesha/ganesha.conf
cat <<EOF | vagrant ssh gluster-server-1 -- "cat | sudo tee $ganesha_conf"
NFS_CORE_PARAM {
    # possible to mount with NFSv3 to NFSv4 Pseudo path
    mount_path_pseudo = true;
    # NFS protocol
    Protocols = 3,4;
}

EXPORT_DEFAULTS {
    Access_Type = RW;
}

LOG {
    components {
        ALL = INFO;
    }
}
EXPORT {
    Export_Id = $TERM;
    # Path will be shown when =showmount=
    Path = $source;
    FSAL {
        name = VFS;
    }
    Access_Type = RW;
    Squash = No_root_squash;
    # Pseudo is used for nfsv4 mount
    Pseudo = $source;
    SecType = sys;
}
EOF
info "Restarting nfs-ganesha"
vagrant ssh gluster-server-1 -- sudo systemctl restart nfs-ganesha
info "Showmount on gluster-server-1"
vagrant ssh gluster-server-1 -- sudo showmount -e localhost


nfs_mnt=/mnt/nfs-$TERM
vagrant ssh gluster-client -- sudo mkdir -p $nfs_mnt
info "Mounting over nfs on client ..."
vagrant ssh gluster-client -- sudo mount -t nfs4 172.21.12.11:/$source $nfs_mnt

value=$(vagrant ssh gluster-client -- sudo cat $nfs_mnt/term)
[[ "$value" == "$TERM" ]] || fail "Cannot read file in mounted dir"

info "SUCCESS !!!!!!!!"