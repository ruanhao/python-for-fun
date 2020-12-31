#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
TOTAL_TASK_STEPS=1

# Join worker nodes to the Kubernetes cluster
cowsay "[TASK 1/$TOTAL_TASK_STEPS (worker)] Join node to Kubernetes Cluster"
apt-get install -y sshpass >/dev/null 2>&1
#sshpass -p "kubeadmin" scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no master:/joincluster.sh /joincluster.sh 2>/dev/null
sshpass -p "kubeadmin" scp -o StrictHostKeyChecking=no master:/joincluster.sh /joincluster.sh
bash /joincluster.sh >/dev/null 2>&1
