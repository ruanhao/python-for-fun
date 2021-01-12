#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: v ssh main -- 'cat | sudo bash ' < test.sh

set -e
# set -x

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


function _persist {
    # info "Psersisting /etc/mdadm.conf ..."
    # mdadm -D --scan > /etc/mdadm.conf # 开机生效
    :
}

function _reset {
    # 扫描并恢复所有磁盘设备
    for host in /sys/class/scsi_host/*; do echo "- - -" | tee $host/scan; ls /dev/sd* ; done
    for i in 0 1 5 6; do
        info "Resetting RAID$i..."
        umount /mnt/md$i 2>/dev/null || true   # 卸载文件系统
        mdadm -S /dev/md$i 2>/dev/null || true # 关闭 raid
        sed -i "/\/dev\/md$i/d" /etc/fstab
        # rm -rf /dev/md$i
    done
    rm -rf /etc/mdadm.conf
    for d in /dev/sd*; do
        if [[ "$d" == *sda* ]]; then
            continue
        fi
        info "Zeroing $d ..."
        mdadm --zero-superblock $d 2>/dev/null || true # 破坏超级块
    done
    info "Reset done"
}

function _stat {
    info "Show stat in /proc"
    cat /proc/mdstat
}

# $1: expected num
function _find_disk_for_raid {
    result=""
    num=$1
    found=0
    for d in /dev/sd*; do
        if [[ "$d" == *sda* ]]; then
            continue
        fi
        check_result=$( mdadm --examine $d 2>&1 || true )
        if echo $check_result | grep -q 'Device or resource busy'; then
            continue
        fi
        if echo $check_result | grep -q "No md superblock detected"; then
            result="$result $d"
            ((found=found+1))
            if [[ "$found" == "$num" ]]; then
                echo $result
                return
            fi
        fi
    done
    alert "Can not find $num free device"
}



function test_raid0 {
    disks=$( _find_disk_for_raid 2 )
    info "Creating RAID0 ($disks) ..."
    mdadm -C /dev/md0 -a yes -l 0 -n 2 $disks
    _persist
    mkfs.xfs -f /dev/md0
    mkdir -p /mnt/md0
    mount /dev/md0 /mnt/md0
    # if ! grep -q '/dev/md0' /etc/fstab; then
    #     echo "/dev/md0     /mnt/md0     xfs     defaults   0 0" >> /etc/fstab
    # fi
    info "Show RAID0 info:"
    mdadm -D /dev/md0
    _stat

    if [[ -z "$1" ]]; then
        return
    fi
    disk_to_corrupt=$( awk '{ print $1 }' <<< $disks )
    info "Deleting disk: $disk_to_corrupt"
    echo "hello" > /mnt/md0/hello.txt
    echo 1 >/sys/block/${disk_to_corrupt/\/dev\//}/device/delete
    i=1
    result=nok
    while (( i < 30 )); do
        if ! ls /mnt/md0/hello.txt; then
            result=ok
            break
        fi
        (( i++ ))
        info "Waiting for file corruption ..."
        sleep 5
    done
    if [[ "$result" == nok ]]; then
        fail "The content of the file should be corrupted, nothing can be grepped"
    fi
}


function test_raid1 {
    disks=$( _find_disk_for_raid 2 )
    info "Creating RAID1 ($disks) ..."
    mdadm -C /dev/md1 --metadata=0.90 -a yes -l 1 -n 2 $disks
    _persist
    mkfs.xfs -f /dev/md1
    mkdir -p /mnt/md1
    mount /dev/md1 /mnt/md1
    # if ! grep -q '/dev/md1' /etc/fstab; then
    #     echo "/dev/md1     /mnt/md1     xfs     defaults   0 0" >> /etc/fstab
    # fi
    info "Show RAID1 info:"
    mdadm -D /dev/md1
    _stat

    if [[ -z "$1" ]]; then
        return
    fi
    disk_to_corrupt=$( awk '{ print $1 }' <<< $disks )
    info "Deleting $disk_to_corrupt"
    echo "hello" > /mnt/md1/hello.txt
    i=1
    result=ok
    while (( i < 10 )); do
        if ! ls /mnt/md1/hello.txt; then
            result=nok
            break
        fi
        (( i++ ))
        info "Waiting for file corruption ..."
        sleep 5
    done
    if [[ "$result" == nok ]]; then
        fail "The content of the file SHOULD NOT be corrupted"
    fi
}


function test_raid5 {
    disks=$( _find_disk_for_raid 3 )
    info "Creating RAID5 ($disks) ..."
    mdadm -C /dev/md5 -a yes -l 5 -n 3 $disks
    _persist
    mkfs.xfs -f /dev/md5
    mkdir -p /mnt/md5
    mount /dev/md5 /mnt/md5
    # if ! grep -q '/dev/md5' /etc/fstab; then
    #     echo "/dev/md5     /mnt/md5     xfs     defaults   0 0" >> /etc/fstab
    # fi
    info "Show RAID5 info:"
    mdadm -D /dev/md5
    _stat

}

function test_raid6 {
    disks=$( _find_disk_for_raid 4 )
    info "Creating RAID6 ($disks) ..."
    mdadm -C /dev/md6 -a yes -l 6 -n 4 $disks
    _persist
    mkfs.xfs -f /dev/md6
    mkdir -p /mnt/md6
    mount /dev/md6 /mnt/md6
    # if ! grep -q '/dev/md6' /etc/fstab; then
    #     echo "/dev/md6     /mnt/md6     xfs     defaults   0 0" >> /etc/fstab
    # fi
    info "Show RAID6 info:"
    mdadm -D /dev/md6
    _stat
}

_reset


# test_raid0
test_raid0 verify_redundancy
# test_raid1
test_raid1 verify_redundancy
test_raid5
test_raid6

info "SUCCESS !!!!!!!!!!!!!!"