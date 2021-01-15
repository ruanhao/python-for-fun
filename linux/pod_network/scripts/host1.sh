echo "10.10.103.92 host2" | tee -a /etc/hosts
cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-br0
DEVICE=br0
TYPE=Bridge
ONBOOT=yes
BOOTPROTO=none
NM_CONTROLLED=no
DELAY=0
IPADDR=172.17.1.254
PREFIX=24
EOF

cat <<'EOF' > /sbin/ifup-local
#!/bin/bash

if [[ "$1" == "br0" ]]; then
    if ! ip netns | grep -q pod-1; then
        ip netns add pod-1
        ip -n pod-1 link add eth0 type veth peer name tap-pod-1 netns 1
        ip link set dev tap-pod-1 master br0
        ip link set dev tap-pod-1 up
        ip netns exec pod-1 ip link set dev eth0 up
        ip netns exec pod-1 ip a a 172.17.1.1/24 dev eth0
        ip netns exec pod-1 ip route add 10.10.103.91 dev eth0
        ip netns exec pod-1 ip route add default via 10.10.103.91 dev eth0
    fi

    if ! ip netns | grep -q pod-2; then
        ip netns add pod-2
        ip -n pod-2 link add eth0 type veth peer name tap-pod-2 netns 1
        ip link set dev tap-pod-2 master br0
        ip link set dev tap-pod-2 up
        ip netns exec pod-2 ip link set dev eth0 up
        ip netns exec pod-2 ip a a 172.17.1.2/24 dev eth0
        ip netns exec pod-2 ip route add 10.10.103.91 dev eth0
        ip netns exec pod-2 ip route add default via 10.10.103.91 dev eth0
    fi

    ip link set dev eth1 promisc on
    ip link set dev eth1 master br0
    ip link set dev br0 address $( cat /sys/class/net/eth1/address )
    ip route del 10.10.103.0/24 dev eth1
    ip route add 10.10.103.0/24 dev br0 src 10.10.103.91
    ip route add 172.17.2.0/24 via 10.10.103.92
else
    # DO_NOTHING
    echo -n ""
fi

EOF

chmod a+x /sbin/ifup-local
systemctl restart network
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip_forward.conf
