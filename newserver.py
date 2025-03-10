#!/usr/bin/python3
import os
import time
import socket
import sqlite3
import threading
import subprocess
import ansible_runner
from utils.ping import ping_cmd
from dotenv import load_dotenv

server_status = False

def status():
    global server_status

    print("Status:")
    print(f"Server Status: {'🟢' if server_status else '🔴'}")
    print()
    print("Connected IPs:")

def help_cmd(cmd=None):
    if(cmd):
        print(f"{cmd} help:")
        print("help type shit")

    else:
        print("ZeroPAM CLI Help")
        print("- commands")

def start_server():
    global server_status

    print("Starting Server...")
    server_status = True
    time.sleep(12)

def main():
    prefix = ""

    if(os.stat("utils/ansible/server_inventory.ini").st_size == 0):
        print("First time use detected! Setting up...")
        subprocess.run('echo "[all]" > /utils/ansible/server_inventory.ini', shell=True, text=True)
        # subprocess.run(f"sed -i '/^[all]/a{ip}' utils/ansible/server_inventory.ini", shell=True, text=True)

    print(r"""

░▒▓████████▓▒░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓██████████████▓▒░  
       ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
     ░▒▓██▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
   ░▒▓██▓▒░  ░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
 ░▒▓██▓▒░    ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░ 
                                                                                                    
    """)
    print("Type help for help!")
    status()

    while True:
        action = input(f"{prefix}\033[0;49;31m> \033[0m")
        if (action.strip() == ""):
            continue

        command = action.split()[0]

        if (command in ("exit", "quit", "q")):
            print("Bye!")
            break

        elif (command == "help"):
            # help
            # help <command>
            if (len(action.split()) == 1):
                help_cmd()
            else:
                help_cmd("placeholder")

        elif (command == "set"):
            # set group <group name> <ip addresses>
            # set arg <arg name> [arg value]
            # set server <on/off>
            # set target <group/ip(s)>
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                print("set action completed")

        elif (command == "exec"):
            # REQ: group or ip(s) enabled
            # exec <command>
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                print("exec action completed")

        elif (command == "ping"):
            # ping <group>
            # ping <ip addresses>
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                ping_cmd(action.split()[1])
                print("ping action completed")

        elif (command == "show"):
            # show status
            # show groups
            # show db
            # show ip
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                print("show command completed")

        else:
            print("Unrecognized command! Type help for help!")
        

if (__name__ == '__main__'):
    main()
        