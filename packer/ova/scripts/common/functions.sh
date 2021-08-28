VIRT_FS="
    /sys
    /proc
    /run
    /dev
    /dev/pts
"

log_info() {
    echo "INFO $@"
}

log_error() {
    echo "ERROR $@"
}

log_banner() {
    echo
    echo "====================================================================="
    echo "$1"
    echo "$2"
    echo "====================================================================="
    echo
}

mount_virtual_filesystems() {
    rootfs=$1
    for f in ${VIRT_FS}; do
        mount -o bind ${f} ${rootfs}${f}
    done
}

umount_virtual_filesystems() {
    rootfs=$1
    for f in ${VIRT_FS}; do
        umount -l ${rootfs}${f} 2>/dev/null || true
    done
}


remotelyCopy(){
    local from=$1
    local to=$2
    local password=$3
    expect -c "
        spawn scp ${from} ${to}
        set timeout 3
        expect {
            password: { send ${password}\r; exp_continue}
            yes/no { send yes\r; exp_continue;}
        }
        set timeout 600
        expect eof
        exit
    "
}

remotelyDelete() {
    local server=$1
    local password=$2
    local dir=$3
    local file_pattern=$4
    local keep_days=$5
    expect -c "
        spawn ssh ${server} find -L ${dir} -mtime +${keep_days} -name \"${file_pattern}\" -delete
        set timeout 180
        expect {
            password: { send ${password}\r; exp_continue;}
            yes/no { send yes\r; exp_continue;}
        }
        sleep 5
        exit
    "
}
