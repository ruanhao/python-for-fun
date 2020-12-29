#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:
sed -e 's/\s*\([\+0-9a-zA-Z]*\).*/\1/' << EOF | sudo fdisk /dev/sdb
o # clear the in memory partition table
n # new partition
p # primary partition
1 # partition number 1
  # default - start at beginning of disk
+3G #
n # new partition
p # primary partition
2 # partion number 2
  # default, start immediately after preceding partition
+3G #
n # new partition
p # primary partition
3 # partion number 3
  # default, start immediately after preceding partition
+3G #
p # print the in-memory partition table
w # write the partition table
EOF
