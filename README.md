# PAM C2 (for educational purposes) (better name TBD)
Custom PAM module that sends login information to a remote server (built for educational purposes to understand how PAM works on the backend)

## Setup:
1. Write all target IP addresses in inventory.ini under the [targets] section
2. Run `sudo bash setup.sh <Callback IP> <Port>` as root from the host machine

## Host Requirements and Prerequities:
Host must be a Linux distribution (Debian-based/RedHat-based for now) capable of installing and running Ansible

Install Ansible on the host machine
- Ubuntu: `sudo apt update && sudo apt install software-properties-common && sudo add-apt-repository --yes --update ppa:ansible/ansible && sudo apt install ansible`
- RedHat Distributions: `sudo dnf install ansible`
- Kali Linux: `sudo apt install ansible`

## Current Progress
- Running setup.sh successfully deploys the module

## Current Known Issues
- idk we'll see

## Todo
- Encrypt message being sent from client
- Create default server-side server with database
- Customizable setup script (output formats, special servers, delivery types)
- Include Arch/SUSE category of target machine (should same as RedHat)