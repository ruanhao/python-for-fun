echo "10.0.1.3 gateway" | tee -a /etc/hosts

yum install epel-release -y
yum install nginx -y

cat <<'EOF' | tee /etc/nginx/conf.d/endpoints.conf
server {
    listen  8080;
    location / {
        return 200 "outside($server_port)\n";
    }
}

server {
    listen  8081;
    location / {
        return 200 "outside($server_port)\n";
    }
}
EOF

systemctl enable nginx
systemctl restart nginx