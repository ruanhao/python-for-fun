#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: 对同一个 glusterfs volume 分别通过 glusterfs 和 nfs 的方式 mount 到客户端
#
#
#                         +-------------------+
#                         |  /mnt/nfs         |
#     +-------------------+-------------------+
#     | /mnt/gfs          |  mount -t nfs     |
#     +-------------------+-------------------+
#     | mount -t glusterfs|    nfs driver     |
#     +-------------------+-------------------+
#     |            glusterfs driver           |
#     +-------------------+-------------------+
#     |          GlusterFS Volumn             |
#     +---------------------------------------+

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

# vagrant ssh gluster-server-1 -- sudo bash /vagrant/delete-all-gfs-volumes.sh

status=$(vagrant ssh gluster-server-1 -- 'sudo gluster peer status')
if echo $status | grep -q 'Number of Peers: 0'; then
    info "Probing for peers ..."
    vagrant ssh gluster-server-1 -- 'sudo gluster peer probe 172.21.12.12 ; sudo gluster peer probe 172.21.12.13'

fi

TERM=$RANDOM
volume_name="myvolume-$TERM"

info "Creating volume [$volume_name] ..."
vagrant ssh gluster-server-1 -- sudo gluster volume create $volume_name replica 3 transport tcp 172.21.12.11:/brick$TERM 172.21.12.12:/brick$TERM 172.21.12.13:/brick$TERM force
info "Starting volume [$volume_name] ..."
vagrant ssh gluster-server-1 -- sudo gluster volume start $volume_name

info "Mounting over glusterfs on client ..."
gfs_mnt=/mnt/gfs-$volume_name
vagrant ssh gluster-client -- "sudo mkdir $gfs_mnt && sudo mount -t glusterfs 172.21.12.11:/$volume_name $gfs_mnt"

info "Preparing nfs-glusterfs conf on server ..."
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
    Path = /$volume_name;
    FSAL {
        name = GLUSTER;
        hostname = 172.21.12.11;
        # Gluster volume name
        volume = ${volume_name};
    }
    Squash = "No_root_squash";
    # Pseudo is used for nfsv4 mount
    Pseudo = /$volume_name;
    SecType = sys;
}
EOF
# echo "%include $ganesha_conf" | vagrant ssh gluster-server-1 -- "cat | sudo tee -a /etc/ganesha/ganesha.conf"
info "Restarting nfs-ganesha"
vagrant ssh gluster-server-1 -- sudo systemctl restart nfs-ganesha
info "Showmount on gluster-server-1"
vagrant ssh gluster-server-1 -- sudo showmount -e localhost


nfs_gfs_mnt=/mnt/nfs-gluster-$volume_name
vagrant ssh gluster-client -- sudo mkdir -p $nfs_gfs_mnt
info "Mounting over nfs-glusterfs on client ..."
vagrant ssh gluster-client -- sudo mount -t nfs4 172.21.12.11:/$volume_name $nfs_gfs_mnt


vagrant ssh gluster-client -- "echo $TERM | sudo tee $nfs_gfs_mnt/term"
value=$(vagrant ssh gluster-client -- sudo cat $gfs_mnt/term)
[[ "$value" == "$TERM" ]] || fail "Files in two mount dir should be in sync"

# info "Show peer status"
# vagrant ssh gluster-server-1 -- sudo gluster peer status
# info "Show volume info"
# vagrant ssh gluster-server-1 -- sudo gluster volume info

info "SUCCESS !!!!!!!!"