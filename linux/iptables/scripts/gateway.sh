echo "172.0.1.2 internal" | tee -a /etc/hosts
echo "10.0.1.2 outside" | tee -a /etc/hosts
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-ip_forward.conf
yum install conntrack -y