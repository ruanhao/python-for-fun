#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:


env GOOS=linux GARCH=amd64 CGO_ENABLED=0 go build main.go
docker build -t ruanhao/kubia .
