#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

# By default, MongoDB instance stores:
# - data files in /var/lib/mongo
# - log files in /var/log/mongodb


version=4.0

# sudo mkdir -p /data/db

cat <<EOF | sudo tee /etc/yum.repos.d/mongodb-org-$version.repo
[mongodb-org-$version]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/amazon/2/mongodb-org/$version/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-$version.asc
EOF

sudo yum install -y mongodb-org

cat <<EOF | sudo tee /etc/mongod.conf
systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

# Where and how to store data.
storage:
  dbPath: /var/lib/mongo
  journal:
    enabled: true


# how the process runs
processManagement:
  fork: true  # fork and run in background
  pidFilePath: /var/run/mongodb/mongod.pid  # location of pidfile
  timeZoneInfo: /usr/share/zoneinfo

# network interfaces
net:
  port: 27017
  bindIp: 0.0.0.0

replication:
  replSetName: "rs0"
EOF

sudo systemctl enable mongod
#sudo chkconfig mongod on
