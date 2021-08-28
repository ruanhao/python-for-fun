set -x
sudo apt update
sudo apt-get install python3-venv -y
# sudo apt install ubuntu-desktop -y
sudo apt install vpnc -y
sudo apt install iperf3 -y

cat <<EOF | sudo tee $HOME/.inputrc
"\C-p": history-search-backward
"\C-n": history-search-forward
EOF
sudo chmod a+wr $HOME/.inputrc
sudo cp $HOME/.inputrc /root
cat <<EOF | sudo tee -a /etc/sudoers
cisco ALL=(ALL) NOPASSWD: ALL
EOF
echo 'export TMOUT=0' >> $HOME/.bashrc

cat <<EOF | sudo tee -a /etc/sudoers
cisco ALL=(ALL) NOPASSWD: ALL
EOF
echo 'export TMOUT=0' >> /home/cisco/.bashrc

cat <<EOF | sudo tee -a $HOME/.bashrc
alias ..='cd ..'
alias ...='.2'
alias ....='.3'
alias .....='.4'
alias ......='.5'
alias .2='cd ../..'
alias .3='cd ../../..'
alias .4='cd ../../../..'
alias .5='cd ../../../../..'
export TMOUT=0
# export https_proxy="http://proxy.esl.cisco.com:8080"
# export http_proxy="http://proxy.esl.cisco.com:8080"
# export no_proxy=10.74.68.44
EOF

echo "KexAlgorithms diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1,diffie-hellman-group1-sha1" | sudo tee -a /etc/ssh/sshd_config.d/weak.conf


# mkdir -p $HOME/.ssh
# echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCvHyNxOnyzDbpCLgp9JnbbBVYz1heAbg7hlYYsqZiTMDyj34XXlT7iXJ7xKZvpEXq8/CRFpCT8Xf+Tz2LqLtTquPAQ7VwQU7rJa0wOvlhl+fizQF438iuiJOHole3pWnTzGXpw5u2W1vWhSO+81Vyh/BUfT1OPW7bAsb0JksKs0wueevlthch+dhv6vh4fZ51HuUgjUajnh7lH0fzxeuCxiGYWvEC8AEKU9ArsKbtTXJ3YQjcJ3A8HU4JG+4qcVEv/XITq0GWb3mJQNAl/s81gzcgeso1xAJDkUq73Q6XDDVDCBM7BOjrPhje4SeNzRWVOT3qA1QnC3wRmYTuBRNqx haoruan@HAORU-M-C0M0" | sudo tee -a $HOME/.ssh/authorized_keys
# sudo chown cisco:cisco $HOME/.ssh
# sudo chown cisco:cisco $HOME/.ssh/authorized_keys