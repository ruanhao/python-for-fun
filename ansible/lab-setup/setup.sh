#/bin/sh

sudo apt-get update


# open password auth for backup if ssh key doesn't work, bydefault, username=vagrant password=vagrant
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
sudo systemctl restart sshd

# install ansible
# sudo yum install -y ansible
sudo apt-get install -y ansible

# edit host file

sudo sh -c "echo 192.168.200.10 ansible-controller >> /etc/hosts"
sudo sh -c "echo 192.168.200.11 ansible-node1 >> /etc/hosts"
sudo sh -c "echo 192.168.200.12 ansible-node2 >> /etc/hosts"

ssh-keygen -b 2048 -t rsa -f ~/.ssh/id_rsa -N ""
mkdir -p ~/.ssh/ && touch ~/.ssh/config && grep -q 'StrictHostKeyChecking' ~/.ssh/config || echo 'StrictHostKeyChecking no' >> ~/.ssh/config