#!/bin/bash

# Install deps and ansible repo
sudo apt update
sudo apt install software-properties-common ca-certificates curl -y
sudo add-apt-repository --yes ppa:ansible/ansible

# Add Docker keyring and repo
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update 

# Install ansible and docker
sudo apt install ansible docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y