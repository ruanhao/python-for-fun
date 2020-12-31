#!/bin/bash

export DEBIAN_FRONTEND=noninteractive
KUBERNETES_VERSION=1.18.14-00
TOTAL_TASK_STEPS=12

apt-get update -y
apt-get install apt-transport-https ca-certificates curl software-properties-common cowsay -y

cowsay "[TASK 1/$TOTAL_TASK_STEPS (common)] Adding apt repo"
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# Add kubernetes sources list into the sources.list directory
cat <<EOF | sudo tee /etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF
apt-get update -y

cowsay "[TASK 2/$TOTAL_TASK_STEPS (common)] Setting Docker auth"
mkdir -p /.docker
cat <<EOF | tee /.docker/config.json
{
    "auths": {
        "https://index.docker.io/v1/": {
            "auth": "cnVhbmhhbzowNjdmMDRkZi1lYWNmLTQwYTItODg3Zi0zOGNmNWQzZDYzZDQ="
        }
    }
}
EOF

# Update hosts file
cowsay "[TASK 3/$TOTAL_TASK_STEPS (common)] Update /etc/hosts file"
cat >>/etc/hosts<<EOF
172.42.42.100 master
172.42.42.101 worker1
172.42.42.102 worker2
EOF


cowsay "[TASK 4/$TOTAL_TASK_STEPS (common)] Install docker container engine"
apt-get install docker-ce -y

# add ccount to the docker group
usermod -aG docker vagrant

# Enable docker service
cowsay "[TASK 5/$TOTAL_TASK_STEPS (common)] Enable and start docker service"
systemctl enable docker >/dev/null 2>&1
systemctl start docker

# Add sysctl settings
cowsay "[TASK 6/$TOTAL_TASK_STEPS (common)] Add sysctl settings"
cat >>/etc/sysctl.d/kubernetes.conf<<EOF
net.bridge.bridge-nf-call-ip6tables = 1
net.bridge.bridge-nf-call-iptables = 1
EOF
sysctl --system >/dev/null 2>&1

# Disable swap
cowsay "[TASK 7/$TOTAL_TASK_STEPS (common)] Disable and turn off SWAP"
sed -i '/swap/d' /etc/fstab
swapoff -a

# Install Kubernetes
cowsay "[TASK 8/$TOTAL_TASK_STEPS (common)] Install Kubernetes kubeadm, kubelet and kubectl"
apt-get install -y \
        kubelet=$KUBERNETES_VERSION \
        kubeadm=$KUBERNETES_VERSION \
        kubectl=$KUBERNETES_VERSION

# Start and Enable kubelet service
cowsay "[TASK 9/$TOTAL_TASK_STEPS (common)] Enable and start kubelet service"
systemctl enable kubelet >/dev/null 2>&1
systemctl start kubelet >/dev/null 2>&1

# Enable ssh password authentication
cowsay "[TASK 10/$TOTAL_TASK_STEPS (common)] Enable ssh password authentication"
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl restart sshd

# Set Root password
cowsay "[TASK 11/$TOTAL_TASK_STEPS (common)] Set root password"
echo -e "kubeadmin\nkubeadmin" | passwd root
#echo "kubeadmin" | passwd --stdin root >/dev/null 2>&1

# Update vagrant user's bashrc file
echo "export TERM=xterm" >> /etc/bashrc

cowsay "[TASK 12/$TOTAL_TASK_STEPS (common)] Preconfigure for glusterfs"
# glusterfs 需要的内核模块支持
modprobe dm_thin_pool
add-apt-repository ppa:gluster/glusterfs-8 -y
apt-get -y install glusterfs-client
# https://github.com/gluster/gluster-kubernetes/issues/510
rm -rf /var/lib/heketi
rm -rf /etc/glusterfs
rm -rf /var/lib/glusterd
rm -rf /var/lib/misc/glusterfsd
