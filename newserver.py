#!/usr/bin/python3
import os
import time
import socket
import sqlite3
import argparse
import threading
import subprocess
import ansible_runner
from utils.ping import ping_cmd
from utils.server import setup, server_args
from dotenv import load_dotenv

server_status = False
server_thread = None
stop_event = threading.Event()

def status():
    global server_status

    print(f"Server Status: {'🟢' if server_status else '🔴'}")
    print()
    print("Connected IPs:")

def help_cmd(cmd=None):
    if(cmd):
        print(f"{cmd} help:")
        print("help")

    else:
        print("ZeroPAM CLI Help")
        print("- commands")

def start_listener(cmd_args):
    global server_status
    global server_thread

    print("Starting Server...")
    server_status = True

    server_thread = threading.Thread(target=setup, args=(cmd_args,stop_event))
    server_thread.daemon = True
    server_thread.start()

def stop_listener():
    global server_status
    global server_thread

    if (not server_thread):
        print("Server not running!")
        return False
    
    print("Stopping Server...")
    stop_event.set()
    server_status = False

def main():
    global server_status
    global server_thread
    prefix = ""
    cmd_args = ""

    if(os.stat(f"./utils/ansible/server_inventory.ini").st_size == 0):
        print("First time use detected! Setting up...")
        subprocess.run(f'echo "[all]" > ./utils/ansible/server_inventory.ini', shell=True, text=True)
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

        if (server_thread):
            if (not server_thread.is_alive()):
                print("Server down!")
                server_status = False

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
            # set target <group/ip(s)>
            # set default <username/password> [username/password]
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

        elif (command == "show"):
            # show status
            # show groups
            # show db
            # show ip
            # show args
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                split_action = action.split()
                if (split_action[1].strip() == "status"):
                    status()
                else:
                    print(f"Unknown argument for server: {split_action[1].strip()}")

        elif (command == "server"):
            # server up
            # server down
            # server args <arg string>
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                split_action = action.split()
                if (split_action[1].strip() == "up"):
                    if (not cmd_args or cmd_args == ""):
                        cmd_args = server_args("")
                        print("Running Server with default arguments")
                        print(cmd_args)
                    start_listener(cmd_args)

                elif (split_action[1].strip() == "down"):
                    stop_listener()

                elif (split_action[1].strip() == "args"):
                    if (len(split_action) == 2):
                        print("Must provide argument when using server args!")
                    elif (split_action[2] == "reset"):
                        print("Server arguments reset!")
                        cmd_args = server_args("")
                    else:
                        try:
                            cmd_args = server_args(" ".join(split_action[2:]))
                            print("Success! New Server Arguments:")
                            print(cmd_args)
                        except (argparse.ArgumentError, SystemExit) as E:
                            print(f"ERROR PARSING ARGUMENTS: {E}")

                else:
                    print(f"Unknown argument for server: {action.split()[1].strip()}")

        else:
            print("Unrecognized command! Type help for help!")
        

if (__name__ == '__main__'):
    main()
        