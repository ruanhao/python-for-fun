#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
TOTAL_TASK_STEPS=6

# Initialize Kubernetes
cowsay "[TASK 1/$TOTAL_TASK_STEPS (master)] Initialize Kubernetes Cluster"
kubeadm init --kubernetes-version=v1.18.14 --apiserver-advertise-address=172.42.42.100 --pod-network-cidr=192.168.0.0/16 | tee /root/kubeinit.log
# 启用 Swagger UI :
# 1. Add --enable-swagger-ui=true to API manifest file /etc/kubernetes/manifests/kube-apiserver.yaml
# 2. Save the file (API pod will restart itself)
# 3. See https://jonnylangefeld.com/blog/kubernetes-how-to-view-swagger-ui

# Copy Kube admin config
cowsay "[TASK 2/$TOTAL_TASK_STEPS (master)] Copy kube admin config to home directory"
mkdir -p /home/vagrant/.kube
mkdir -p /root/.kube
cp /etc/kubernetes/admin.conf /home/vagrant/.kube/config
cp /etc/kubernetes/admin.conf /root/.kube/config
chown -R vagrant:vagrant /home/vagrant/.kube

# Deploy flannel network
cowsay "[TASK 3/$TOTAL_TASK_STEPS (master)] Deploy Calico network"
kubectl create -f https://docs.projectcalico.org/v3.9/manifests/calico.yaml

cowsay "[TASK 4/$TOTAL_TASK_STEPS (master)] Deploy metrics-server" # you can use `kubectl top` then
patch /vagrant/k8s_bootstrap/metrics-server-components-v0.4.1.yaml \
      -i /vagrant/k8s_bootstrap/metrics-server-components.patch -o - | kubectl create -f -

# Generate Cluster join command
cowsay "[TASK 5/$TOTAL_TASK_STEPS (master)] Generate and save cluster join command to /joincluster.sh"
kubeadm token create --print-join-command | tee /joincluster.sh

cowsay "[TASK 6/$TOTAL_TASK_STEPS (master)] Customize bashrc"
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
alias kc=kubectl
alias k=kubectl
complete -F __start_kubectl kc
complete -F __start_kubectl k

source /etc/kube-ps1.sh
# export PS1='[\u@\h \W $(kube_ps1)]\$ '
export PS1='$(kube_ps1)\$ '
EOF

cat <<EOF | sudo -u vagrant tee /home/vagrant/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF