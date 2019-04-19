#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

var_file=$1

packer build -var-file $var_file ubuntu-16.04-amd64.json
