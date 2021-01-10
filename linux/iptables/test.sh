#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Description:

set -e


info () {
    echo -e $(date +"%T") - "\033[0;32m$@\033[0m"
}

alert () {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
}

fail() {
    echo -e $(date +"%T") - "\033[0;31m$@\033[0m"
    exit 1
}


flush() {
    if [[ "x$1" == "x" ]]; then
        for h in outside gateway internal; do
            info "Flushing iptables on $h ..."
            vagrant ssh $h -- 'sudo iptables -F; sudo iptables -t nat -F'
        done
    else
        info "Flushing iptables on $1 ..."
        vagrant ssh $1 -- 'sudo iptables -F; sudo iptables -t nat -F'
    fi

}


function test_protocol() {
    # -p 选项支持如下协议类型：
    # tcp, udp, udplite, icmp, icmpv6, esp, ah, sctp, mh
    info "测试协议类型"
    flush
    vagrant ssh gateway -- curl -s outside:8080 || fail "outside:8080 should be accessible"
    vagrant ssh outside -- sudo iptables -I INPUT -s 10.0.1.3 -p tcp -j REJECT
    vagrant ssh outside -- sudo iptables -L -vn --line
    vagrant ssh gateway -- curl -s outside:8080 && fail "outside:8080 should be inaccessible for TCP"
    vagrant ssh gateway -- ping outside -c 1 || fail "ICMP is ok"
    # TCP 连接被拒绝了，但是可以发送 ping 请求
}

function test_log() {
    local term=$RANDOM
    info "测试 LOG [$term]"
    flush
    vagrant ssh outside -- "echo kern.warning /var/log/iptables$term.log | sudo tee /etc/rsyslog.d/iptables.conf; sudo systemctl restart rsyslog"
    vagrant ssh outside -- sudo iptables -I INPUT -p tcp --dport 8081 -j LOG --log-prefix 8081-$term
    vagrant ssh gateway -- curl -s outside:8081
    vagrant ssh outside -- "sudo tail /var/log/iptables$term.log"
}


function test_snat() {
    info "测试 SNAT"
    flush
    vagrant ssh internal -- curl --connect-timeout 1 -s outside:8080 && fail "Should be connection timeout before SNAT"
    vagrant ssh gateway -- sudo iptables -t nat -A POSTROUTING -s 172.0.1.0/24 -j SNAT --to-source 10.0.1.3
    vagrant ssh internal -- curl --connect-timeout 1 -s outside:8080 || fail "Should be ok after SNAT"
    vagrant ssh gateway -- sudo conntrack -L -s 172.0.1.2 # check conntrack ，可以使用 conntrack -E -s 172.0.1.2 进行实时监控
}

function test_dnat() {
    info "测试 DNAT"
    flush
    vagrant ssh outside -- curl --connect-timeout 1 -s gateway:8080 && fail "Should be connection timeout before DNAT"
    vagrant ssh gateway -- sudo iptables -t nat -I PREROUTING -d 10.0.1.3 -p tcp --dport 8080 -j DNAT --to-destination 172.0.1.2:8080
    vagrant ssh outside -- curl --connect-timeout 1 -s gateway:8080 || fail "Should be ok after DNAT"
    vagrant ssh gateway -- sudo conntrack -L -d 10.0.1.3
}

function test_redirect() {
    info "测试本地端口转发"
    flush
    vagrant ssh gateway -- curl --connect-timeout 1 -s outside:48080 && fail "Should not be ok before REDIRECT"
    vagrant ssh outside -- sudo iptables -t nat -A PREROUTING -d 10.0.1.2 -p tcp --dport 48080 -j REDIRECT --to-port 8080
    # 若 8080 监听于 localhost，则可能需要执行：sysctl -w net.ipv4.conf.all.route_localnet=1
    vagrant ssh gateway -- curl --connect-timeout 1 -s outside:48080 || fail "Should be ok after REDIRECT"
}


# test_protocol
# test_log
# test_snat
# test_dnat
test_redirect


# flush >/dev/null
info "SUCCESS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
