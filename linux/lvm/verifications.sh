#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description: cat verifications.sh | vagrant ssh main -- 'cat | sudo bash '

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

function cleanup() {
    for vg in $(vgs --no-headings -o vg_name); do
        for lv in /dev/$vg/*; do
            umount $lv || true
        done
        vgremove -y $vg
    done
    for pv in $(pvs --noheadings -o pv_name); do
        pvremove -y $pv
        dd if=/dev/urandom of=$pv bs=1M count=64
    done
}

cleanup

TERM=$RANDOM
VG_NAME=vg$TERM
LV_NAME=lv$TERM

info "===== 创建物理卷 ====="
pvcreate /dev/sdb[1,2,3] # 创建 3 个物理卷
info "===== 查看物理卷 ====="
pvdisplay
info "===== 将物理卷合成卷组 ====="
vgcreate $VG_NAME /dev/sdb1 /dev/sdb2 # 将其中 2 个物理卷合成卷组
info "===== 查看卷组 ====="
vgdisplay
info "====== 在卷组之上创建逻辑卷 ====="
lvcreate -L 1G -n $LV_NAME $VG_NAME
info "====== 查看逻辑卷 ====="
lvdisplay

mkdir -p /mnt/$LV_NAME
info "====== 格式化逻辑卷 ====="
mkfs.ext4 /dev/$VG_NAME/$LV_NAME
info "====== 挂载逻辑卷 ====="
mount /dev/$VG_NAME/$LV_NAME /mnt/$LV_NAME

info "===== 扩充卷组容量 ====="
vgextend $VG_NAME /dev/sdb3 # 扩充卷组容量
info "===== 扩展逻辑卷容量 ====="
lvextend -L +1G /dev/$VG_NAME/$LV_NAME # 扩充逻辑卷容量
info "====== 查看逻辑卷 ====="
lvdisplay
info "====== 查看挂载情况 ====="
df -h # 文件系统未反映新增的容量
size0=$(df | grep $LV_NAME | awk '{print $2}')
info "====== 通知文件系统更新容量 ====="
resize2fs /dev/$VG_NAME/$LV_NAME
df -h
size1=$(df | grep $LV_NAME | awk '{print $2}')
increment=$(bc <<< "($size1 - $size0) / 1024 / 1000") # 大致增长 1G
[[ "$increment" == 1 ]] || fail "Wrong FS capacity increment"

info "SUCCESS !!!!!!!!!!!!!!!"