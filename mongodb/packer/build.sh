#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

var_file=$1

if [[ -z $var_file ]]; then
   echo "Region var file must be specified."
   exit 1
fi

packer build -var-file $var_file linux2-mongo.json
