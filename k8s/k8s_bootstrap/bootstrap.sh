#!/bin/bash

KUBERNETES_VERSION=1.18.12-00

cat <<EOF | sudo -u vagrant tee /home/vagrant/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF

# Update hosts file
echo "[TASK 1] Update /etc/hosts file"
cat >>/etc/hosts<<EOF
172.42.42.100 master
172.42.42.101 worker1
172.42.42.102 worker2
EOF


echo "[TASK 2] Adding apt repo"
apt-get update -y
apt-get install apt-transport-https ca-certificates curl software-properties-common -y

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# Add kubernetes sources list into the sources.list directory
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update -y

echo "[TASK 3] Install docker container engine"
apt-get install docker-ce -y

# add ccount to the docker group
usermod -aG docker vagrant

# Enable docker service
echo "[TASK 4] Enable and start docker service"
systemctl enable docker >/dev/null 2>&1
systemctl start docker

# Add sysctl settings
echo "[TASK 5] Add sysctl settings"
cat >>/etc/sysctl.d/kubernetes.conf<<EOF
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system >/dev/null 2>&1

# Disable swap
echo "[TASK 6] Disable and turn off SWAP"
sed -i '/swap/d' /etc/fstab
swapoff -a

# Install Kubernetes
echo "[TASK 7] Install Kubernetes kubeadm, kubelet and kubectl"
apt-get install -y \
        kubelet=$KUBERNETES_VERSION \
        kubeadm=$KUBERNETES_VERSION \
        kubectl=$KUBERNETES_VERSION

# Start and Enable kubelet service
echo "[TASK 8] Enable and start kubelet service"
systemctl enable kubelet >/dev/null 2>&1
systemctl start kubelet >/dev/null 2>&1

# Enable ssh password authentication
echo "[TASK 9] Enable ssh password authentication"
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl restart sshd

# Set Root password
echo "[TASK 10] Set root password"
echo -e "kubeadmin\nkubeadmin" | passwd root
#echo "kubeadmin" | passwd --stdin root >/dev/null 2>&1

# Update vagrant user's bashrc file
echo "export TERM=xterm" >> /etc/bashrc

echo "[TASK 10] Preconfigure for glusterfs"
# glusterfs 需要的内核模块支持
modprobe dm_thin_pool
add-apt-repository ppa:gluster/glusterfs-8 -y
apt-get -y install glusterfs-client
# https://github.com/gluster/gluster-kubernetes/issues/510
rm -rf /var/lib/heketi
rm -rf /etc/glusterfs
rm -rf /var/lib/glusterd
rm -rf /var/lib/misc/glusterfsd
