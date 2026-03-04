import socket
import sys
import os
import re

def handle_client(client_socket):
    try:
        request = client_socket.recv(4096).decode('utf-8', errors='ignore')
        if not request:
            return

        print(f"--- New Request ---\n{request.splitlines()[0]}")

        lines = request.split('\r\n')
        first_line = lines[0].split()

        if len(first_line) < 3:
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
            return

        method, url, version = first_line

        if method != "GET":
            client_socket.sendall(b"HTTP/1.0 501 Not Implemented\r\n\r\n")
            return

        url_match = re.match(r'http://([^/:]+)(?::(\d+))?(/.*)?', url)
        if not url_match:
            client_socket.sendall(b"HTTP/1.0 400 Bad Request\r\n\r\n")
            return

        host = url_match.group(1)
        port = int(url_match.group(2)) if url_match.group(2) else 80
        path = url_match.group(3) if url_match.group(3) else "/"

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port))

        new_request = f"{method} {path} {version}\r\n"
        for line in lines[1:]:
            if line.startswith("Proxy-Connection:"):
                new_request += "Connection: close\r\n"
            else:
                new_request += line + "\r\n"
        
        server_socket.sendall(new_request.encode())

        while True:
            data = server_socket.recv(4096)
            if len(data) > 0:
                client_socket.sendall(data)
            else:
                break
        
        server_socket.close()

    except Exception as e:
        pass
    finally:
        client_socket.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 proxy.py <port>")
        sys.exit(1)

    port = int(sys.argv[1])
    
    proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_server.bind(('0.0.0.0', port))
    proxy_server.listen(100)
    
    print(f"Proxy server running on port {port}...")

    while True:
        client_socket, addr = proxy_server.accept()
        
        pid = os.fork()
        if pid == 0:
            proxy_server.close()
            handle_client(client_socket)
            os._exit(0)
        else:
            client_socket.close()

if __name__ == "__main__":
    main()