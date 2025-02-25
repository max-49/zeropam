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

    server_socket.listen()
    print(f"Server listening for incoming connections...")

    while True:
        client_socket, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_socket,addr))
        client_thread.start()

if (__name__ == '__main__'):
    main()