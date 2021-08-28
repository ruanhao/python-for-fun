set -x
sudo apt update

# Install new version Python3
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.8 -y
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2
sudo apt install python3.8-distutils -y
# sudo apt install python3-pip python3.8-dev -y
sudo apt-get install python-virtualenv -y

