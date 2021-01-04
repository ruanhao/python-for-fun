#!/bin/bash

echo "downloading kafka...$KAFKA_VERSION"

#download kafka binaries if not present
if [ ! -f  $KAFKA_TARGET/$KAFKA_NAME.tgz ]; then
   mkdir -p $KAFKA_TARGET
   wget -O "$KAFKA_TARGET/$KAFKA_NAME.tgz" https://archive.apache.org/dist/kafka/"$KAFKA_VERSION/$KAFKA_NAME.tgz"
fi

echo "installing JDK and Kafka..."

su -c "yum -y install java-1.8.0-openjdk-devel"

#disabling iptables
/etc/init.d/iptables stop

if [ ! -d $KAFKA_NAME ]; then
   tar -zxvf $KAFKA_TARGET/$KAFKA_NAME.tgz
fi

chown vagrant:vagrant -R $KAFKA_NAME

echo "done installing JDK and Kafka..."

# chmod scripts
chmod u+x /vagrant/scripts/*.sh

cat <<EOF | sudo -u vagrant tee /home/vagrant/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF

cat <<'EOF' | tee -a /home/vagrant/.bashrc
alias ll="ls -lhrt"
alias ..='cd ..'
alias ...='.2'
alias ....='.3'
alias .....='.4'
alias ......='.5'
alias .2='cd ../..'
alias .3='cd ../../..'
alias .4='cd ../../../..'
alias .5='cd ../../../../..'
EOF

if [[ `hostname` == "broker1" ]]; then
    wget http://repos.fedorapeople.org/repos/dchen/apache-maven/epel-apache-maven.repo -O /etc/yum.repos.d/epel-apache-maven.repo
    yum install apache-maven -y
fi