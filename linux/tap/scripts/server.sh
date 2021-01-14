echo "172.0.0.10 client" | tee -a /etc/hosts

# cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-eth1:0
# DEVICE=eth1:0
# IPADDR=172.0.0.100
# PREFIX=24
# ONPARENT=yes
# EOF

# systemctl restart network
ip route del 172.0.0.0/24 || true

cat <<EOF > /usr/lib/systemd/system/socat-tap-server.service
[Unit]
Description=Socat tap server
After=network.target

[Service]
EnvironmentFile=-/etc/tap.env
ExecStart=/bin/bash -c 'exec socat tcp-l:40839,reuseaddr TUN:172.0.0.1/24,iff-no-pi,up,tun-type=tap'
Type=simple
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl enable socat-tap-server
systemctl start socat-tap-server
