#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

VERSION=v1
env GOOS=linux GARCH=amd64 CGO_ENABLED=0 go build main.go || exit 1
docker build -t ruanhao/kubia:$VERSION . || exit 1
docker push ruanhao/kubia:$VERSION || exit 1
