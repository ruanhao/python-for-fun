echo "10.74.68.10 client" | tee -a /etc/hosts

yum install bridge-utils -y

cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-br0
DEVICE=br0
TYPE=Bridge
ONBOOT=yes
BOOTPROTO=none
NM_CONTROLLED=no
DELAY=0
IPADDR=10.74.68.85
PREFIX=24
EOF

cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-eth2
BOOTPROTO=none
ONBOOT=yes
DEVICE=eth2
NM_CONTROLLED=no
BRIDGE=br0
EOF

systemctl restart network
