#!/bin/bash

# -------------------------------------------------------------------
# Infra server URL information
# -------------------------------------------------------------------
: ${ARTIFACT_SERVER="10.74.68.44"}
: ${ARTIFACT_SERVER_USER="nexus"}
: ${ARTIFACT_SERVER_PWD="nexus"}
: ${DNS_SERVERS="171.70.168.183 173.36.131.10"}
: ${PYPI_OPTS="--trusted-host ${ARTIFACT_SERVER}"}
: ${PYPI_URL="http://${ARTIFACT_SERVER}:8081"}

export ARTIFACT_SERVER ARTIFACT_SERVER_USER ARTIFACT_SERVER_PWD DNS_SERVERS PYPI_OPTS PYPI_URL

# -------------------------------------------------------------------
# user/group information
# -------------------------------------------------------------------
: ${DEFAULT_USER_GROUP_ID="1234"}
: ${DEFAULT_USER_GROUP="cisco"}

: ${DEFAULT_USER_ID="1234"}
: ${DEFAULT_USERNAME="cisco"}
: ${DEFAULT_PASSWORD="cisco"}

export DEFAULT_USER_GROUP_ID DEFAULT_USER_GROUP DEFAULT_USER_ID DEFAULT_USERNAME DEFAULT_PASSWORD

