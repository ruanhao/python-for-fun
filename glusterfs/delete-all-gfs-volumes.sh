#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

if gluster volume list | grep -q 'No volumes'; then
    exit 0
fi

for vol in $( gluster volume list ); do
    yes | gluster volume stop $vol
    yes | gluster volume delete $vol
done