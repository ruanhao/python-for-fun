echo "10.10.103.91 host1" | tee -a /etc/hosts
cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-br0
DEVICE=br0
TYPE=Bridge
ONBOOT=yes
BOOTPROTO=none
NM_CONTROLLED=no
DELAY=0
IPADDR=172.17.2.254
PREFIX=24
EOF

cat <<'EOF' > /sbin/ifup-local
#!/bin/bash

if [[ "$1" == "br0" ]]; then
    if ! ip netns | grep -q pod-3; then
        ip netns add pod-3
        ip -n pod-3 link add eth0 type veth peer name tap-pod-3 netns 1
        ip link set dev tap-pod-3 master br0
        ip link set dev tap-pod-3 up
        ip netns exec pod-3 ip link set dev eth0 up
        ip netns exec pod-3 ip a a 172.17.2.3/24 dev eth0
        ip netns exec pod-3 ip route add 10.10.103.92 dev eth0
        ip netns exec pod-3 ip route add default via 10.10.103.92 dev eth0
    fi

    if ! ip netns | grep -q pod-4; then
        ip netns add pod-4
        ip -n pod-4 link add eth0 type veth peer name tap-pod-4 netns 1
        ip link set dev tap-pod-4 master br0
        ip link set dev tap-pod-4 up
        ip netns exec pod-4 ip link set dev eth0 up
        ip netns exec pod-4 ip a a 172.17.2.4/24 dev eth0
        ip netns exec pod-4 ip route add 10.10.103.92 dev eth0
        ip netns exec pod-4 ip route add default via 10.10.103.92 dev eth0
    fi

    ip link set dev eth1 promisc on
    ip link set dev eth1 master br0
    ip link set dev br0 address $( cat /sys/class/net/eth1/address )
    ip route del 10.10.103.0/24 dev eth1
    ip route add 10.10.103.0/24 dev br0 src 10.10.103.92
    ip route add 172.17.1.0/24 via 10.10.103.91
else
    # DO_NOTHING
    echo -n ""
fi

EOF

chmod a+x /sbin/ifup-local
systemctl restart network
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip_forward.conf
