#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e
set -x

vagrant destroy -f || true

vagrant up

vagrant ssh master -- bash /vagrant/k8s_bootstrap/install_glusterfs.sh
