#!/bin/bash

# Initialize Kubernetes
echo "[TASK 1] Initialize Kubernetes Cluster"
kubeadm init --apiserver-advertise-address=172.42.42.100 --pod-network-cidr=192.168.0.0/16 | tee /root/kubeinit.log
# 启用 Swagger UI :
# 1. Add --enable-swagger-ui=true to API manifest file /etc/kubernetes/manifests/kube-apiserver.yaml
# 2. Save the file (API pod will restart itself)
# 3. See https://jonnylangefeld.com/blog/kubernetes-how-to-view-swagger-ui

# Copy Kube admin config
echo "[TASK 2] Copy kube admin config to Vagrant user .kube directory"
mkdir /home/vagrant/.kube
cp /etc/kubernetes/admin.conf /home/vagrant/.kube/config
chown -R vagrant:vagrant /home/vagrant/.kube

# Deploy flannel network
echo "[TASK 3] Deploy Calico network"
su - vagrant -c "kubectl create -f https://docs.projectcalico.org/v3.9/manifests/calico.yaml"

# Generate Cluster join command
echo "[TASK 4] Generate and save cluster join command to /joincluster.sh"
kubeadm token create --print-join-command | tee /joincluster.sh

apt-get install bash-completion -y
kubectl completion bash > /etc/bash_completion.d/kubectl
curl -o /etc/kube-ps1.sh https://raw.githubusercontent.com/jonmosco/kube-ps1/master/kube-ps1.sh
cat <<'EOF' | tee -a /home/vagrant/.bashrc
alias ll="ls -lhrt"
alias ..='cd ..'
alias ...='.2'
alias ....='.3'
alias .....='.4'
alias ......='.5'
alias .2='cd ../..'
alias .3='cd ../../..'
alias .4='cd ../../../..'
alias .5='cd ../../../../..'

alias kcd='kubectl config set-context $(kubectl config current-context) --namespace '
alias kb=kubectl
complete -F __start_kubectl kb

source /etc/kube-ps1.sh
export PS1='[\u@\h \W $(kube_ps1)]\$ '
EOF
