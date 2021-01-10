# echo "172.168.1.2 client" | tee -a /etc/hosts
# sysctl -w net.ipv4.ip_forward=1
# echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip_forward.conf
# yum install conntrack -y

cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-lo
DEVICE=lo

IPADDR0=127.0.0.1
NETMASK0=255.0.0.0
NETWORK0=127.0.0.0
BROADCAST0=127.255.255.255
# If you're having problems with gated making 127.0.0.0/8 a martian,
# you can change this to something else (255.255.255.255, for example)
IPADDR1=10.74.68.58
NETMASK1=255.255.255.255

ONBOOT=yes
NAME=loopback
EOF

systemctl restart network