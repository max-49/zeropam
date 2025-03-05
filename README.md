# PAM C2 (for educational purposes) (A.K.A ZeroPAM)
Custom PAM module proxies all authentication requests and sends credentials to a remote server (built for educational purposes to understand how PAM works on the backend)

## Setup:
1. Write all target IP addresses in inventory.ini under the [targets] section
2. Run `python3 setup.py -i <Callback IP> -p <Port>` from the host machine

## Host Requirements and Prerequities:
Host must be a Linux distribution (Debian-based/RedHat-based for now) capable of installing and running Ansible

Install Ansible on the host machine
- Ubuntu/Debian: `sudo apt update && sudo apt install software-properties-common && sudo add-apt-repository --yes --update ppa:ansible/ansible && sudo apt install ansible`
- RedHat Distributions: `sudo dnf install ansible`
- Kali Linux: `sudo apt install ansible`

Install pip on the host machine
- Ubuntu/Debian/Kali: `sudo apt install python3-pip`
- RedHat Distributions: `sudo dnf install python3-pip`

Install required python modules
- All Distributions: `pip3 install -r requirements.txt`

## Current Known Issues
- idk we'll see

## Todo
- Encrypt message being sent from client
- Create C2 to go alongside ZeroPAM
- Include Arch/SUSE category of target machine