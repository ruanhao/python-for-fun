echo "172.0.1.254 gateway" | tee -a /etc/hosts
echo "10.0.1.2 outside" | tee -a /etc/hosts

ip route add 10.0.1.0/24 via 172.0.1.254
echo '10.0.1.0/24 via 172.0.1.254 dev eth1' > /etc/sysconfig/network-scripts/route-eth1

yum install epel-release -y
yum install nginx -y


cat <<'EOF' | tee /etc/nginx/conf.d/endpoints.conf
server {
    listen  8080;
    location / {
        return 200 "internal($server_port)\n";
    }
}

server {
    listen  8081;
    location / {
        return 200 "internal($server_port)\n";
    }
}
EOF

systemctl enable nginx
systemctl restart nginx
