#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

sudo yum update -y
sudo yum install python-setuptools -y
sudo easy_install pip
