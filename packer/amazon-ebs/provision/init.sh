#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

sudo apt-get update -y
sudo apt-get upgrade -y

. $SCRIPTPATH/install_python3.sh
