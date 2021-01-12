# echo "172.168.1.2 client" | tee -a /etc/hosts
# sysctl -w net.ipv4.ip_forward=1
# echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip_forward.conf
# yum install conntrack -y

cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-lo:0
DEVICE=lo:0
IPADDR=10.74.68.58
PREFIX=32
ONPARENT=yes
EOF

systemctl restart network