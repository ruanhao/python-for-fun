echo "172.0.0.100 server" | tee -a /etc/hosts

# cat <<EOF > /etc/sysconfig/network-scripts/ifcfg-eth1:0
# DEVICE=eth1:0
# IPADDR=172.0.0.10
# PREFIX=24
# ONPARENT=yes
# EOF

# systemctl restart network
ip route del 172.0.0.0/24 || true


cat <<EOF > /usr/lib/systemd/system/socat-tap-client.service
[Unit]
Description=Socat tap client
After=network.target

[Service]
EnvironmentFile=-/etc/tap.env
ExecStart=/bin/bash -c 'exec socat tcp:10.74.68.100:40839 TUN:172.0.0.2/24,iff-no-pi,up,tun-type=tap'
Type=simple
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

systemctl enable socat-tap-client
systemctl start socat-tap-client
