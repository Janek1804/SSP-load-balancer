#!/bin/bash

if [[ $EUID -ne 0 ]]; then
    echo "[install] This script must be run as root!" 1>&2
    exit 1
fi

apt-get update

echo "[install] Installing ansible..."
apt-get -y install ansible

echo "[install] Cloning Containernet repository..."
git clone https://github.com/containernet/containernet.git

echo "[install] Running ansible play..."
ansible-playbook -i "localhost," -c local containernet/ansible/install.yml

echo "[install] Preparing python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip3 install ./containernet

echo "[install] Installed Containernet."
echo "[install] Use .venv/bin/python3 to access Containernet API instead of Mininet API."
