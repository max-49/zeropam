import socket
import threading

PORT = 5000

def handle_client(c, addr):
    data = c.recv(1024).decode()
    print(f"Received from {addr} - {data}")
    c.close()

def main():
    server_socket = socket.socket()
    print("Created socket")

    server_socket.bind(('', PORT))
    print(f"Socket bound to port {PORT}")

    while True:
        # The server continuously listens for incoming client connections.
        client_socket, addr = server_socket.accept()
        # When a new client connects, a new thread is created to handle the client.
        client_thread = threading.Thread(target=handle_client, args=(client_socket,addr))
        client_thread.start()