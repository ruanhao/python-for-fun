#!/bin/bash

yum install -y tcpdump

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
