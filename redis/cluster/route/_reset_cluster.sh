#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

. _common.sh

info "Resetting nodes ..."
for i in {1..3}; do
    info "Resetting master$i ..."
    vagrant ssh master$i -- redis-cli cluster reset
    info "Resetting slave$i ..."
    vagrant ssh slave$i -- redis-cli cluster reset
    # info "Stopping master$i ..."
    # vagrant ssh master$i -- sudo service redis-server stop
    # info "Stopping slave$i ..."
    # vagrant ssh slave$i -- sudo service redis-server stop
    # info "Removing conf for master$i ..."
    # vagrant ssh master$i -- sudo rm -rf /var/redis/*
    # info "Removing conf for slave$i ..."
    # vagrant ssh slave$i -- sudo rm -rf /var/redis/*
done
# for i in {1..4}; do
#     info "Starting master$i ..."
#     vagrant ssh master$i -- sudo service redis-server start
#     info "Starting slave$i ..."
#     vagrant ssh slave$i -- sudo service redis-server start
# done
info "Resetting nodes done"
