import sys
import os
import socket
import threading
from datetime import datetime
import json

class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    RESET = '\033[0m'

class Server:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients = []
        self.shared_space = None
        self.file_list = []
    
    def set_shared_space(self, shared_space):
        """Set the shared directory path"""
        self.shared_space = shared_space
        self.refresh_file_list()
    
    def refresh_file_list(self):
        """Refresh the list of files in shared directory"""
        if not self.shared_space or not os.path.exists(self.shared_space):
            self.file_list = []
            return
        
        try:
            self.file_list = []
            with os.scandir(self.shared_space) as entries:
                for entry in entries:
                    if entry.is_file():
                        file_info = {
                            'name': entry.name,
                            'size': entry.stat().st_size,
                            'modified': entry.stat().st_mtime
                        }
                        self.file_list.append(file_info)
        except Exception as e:
            print(f"{Colors.RED}Error refreshing file list: {e}{Colors.RESET}")
            self.file_list = []
    
    def start_server(self):
        """Start the server in a separate thread"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            # Get local IP address for display
            local_ip = self.get_local_ip()
            
            print(f"{Colors.GREEN}Server started successfully!{Colors.RESET}")
            print(f"{Colors.CYAN}Server listening on:{Colors.RESET}")
            print(f"{Colors.CYAN}  Local:  http://localhost:{self.port}{Colors.RESET}")
            print(f"{Colors.CYAN}  Network: http://{local_ip}:{self.port}{Colors.RESET}")
            print(f"{Colors.YELLOW}Shared space: {self.shared_space}{Colors.RESET}")
            print(f"{Colors.YELLOW}Files available: {len(self.file_list)}{Colors.RESET}")
            print(f"{Colors.YELLOW}Waiting for client connections...{Colors.RESET}")
            
            # Start accepting connections in a separate thread
            server_thread = threading.Thread(target=self.accept_connections)
            server_thread.daemon = True
            server_thread.start()
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Failed to start server: {e}{Colors.RESET}")
            return False
    
    def get_local_ip(self):
        """Get the local IP address of the machine"""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                print(f"{Colors.GREEN}New connection from {client_address[0]}:{client_address[1]}{Colors.RESET}")
                
                # Add client to list
                self.clients.append((client_socket, client_address))
                
                # Handle client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}Error accepting connection: {e}{Colors.RESET}")
    
    def handle_client(self, client_socket, client_address):
        """Handle communication with a connected client"""
        client_ip = client_address[0]
        try:
            while self.running:
                # Receive data from client
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"{Colors.CYAN}[{timestamp}] Command from {client_ip}: {Colors.WHITE}{data}{Colors.RESET}")
                
                # Parse command
                if data.startswith("UPLOAD:"):
                    # Format: UPLOAD:filename:filesize
                    parts = data.split(":")
                    if len(parts) == 3:
                        filename = parts[1]
                        file_size = int(parts[2])
                        self.receive_file_simple(client_socket, filename, file_size)
                        continue
                elif data.startswith("GET_FILE "):
                    file_index = int(data[9:])
                    self.send_file(file_index, client_socket)
                    continue
                else:
                    response = self.process_command(data)
                    if response:
                        client_socket.send(response.encode('utf-8'))
                
        except Exception as e:
            print(f"{Colors.RED}Error with client {client_ip}: {e}{Colors.RESET}")
        finally:
            # Clean up
            client_socket.close()
            self.clients = [c for c in self.clients if c[1] != client_address]
            print(f"{Colors.YELLOW}Client {client_ip} disconnected{Colors.RESET}")
    
    def process_command(self, command):
        """Process client commands"""
        try:
            if command == "LIST_FILES":
                return self.list_files()
            elif command.startswith("FILE_INFO "):
                file_index = int(command[10:])
                return self.get_file_info(file_index)
            else:
                # Regular message
                return f"Server received: {command}"
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def list_files(self):
        """List all files in the shared directory"""
        self.refresh_file_list()
        return json.dumps({'type': 'file_list', 'files': self.file_list})
    
    def get_file_info(self, file_index):
        """Get information about a specific file by index"""
        if not self.file_list or file_index < 0 or file_index >= len(self.file_list):
            return "ERROR: Invalid file index"
        
        try:
            file_info = self.file_list[file_index]
            filename = file_info['name']
            filepath = os.path.join(self.shared_space, filename)
            
            if not os.path.exists(filepath):
                return "ERROR: File not found on disk"
            
            stat = os.stat(filepath)
            file_info = {
                'type': 'file_info',
                'index': file_index,
                'name': filename,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'readable': os.access(filepath, os.R_OK)
            }
            return json.dumps(file_info)
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def send_file(self, file_index, client_socket):
        """Send a file to the client by index"""
        if not self.file_list or file_index < 0 or file_index >= len(self.file_list):
            client_socket.send("ERROR: Invalid file index".encode('utf-8'))
            return
        
        try:
            file_info = self.file_list[file_index]
            filename = file_info['name']
            filepath = os.path.join(self.shared_space, filename)
            
            if not os.path.exists(filepath):
                client_socket.send("ERROR: File not found on disk".encode('utf-8'))
                return
            
            file_size = os.path.getsize(filepath)
            
            # Send file info first
            file_info_response = json.dumps({
                'type': 'file_transfer',
                'name': filename,
                'size': file_size
            })
            client_socket.send(file_info_response.encode('utf-8'))
            
            # Wait for client acknowledgment
            ack = client_socket.recv(1024).decode('utf-8')
            if ack != "READY":
                return
            
            # Send file content
            print(f"{Colors.YELLOW}Sending file: {filename} ({file_size} bytes){Colors.RESET}")
            with open(filepath, 'rb') as f:
                file_data = f.read()
                client_socket.send(file_data)
            
            print(f"{Colors.GREEN}File sent successfully: {filename}{Colors.RESET}")
            
        except Exception as e:
            print(f"{Colors.RED}Error sending file: {e}{Colors.RESET}")
    
    def receive_file_simple(self, client_socket, filename, file_size):
        """ULTRA SIMPLE: Receive a file from a client"""
        try:
            filepath = os.path.join(self.shared_space, filename)
            
            print(f"{Colors.YELLOW}Receiving file: {filename} ({file_size} bytes){Colors.RESET}")
            
            # Just receive all data at once
            received_data = b""
            while len(received_data) < file_size:
                chunk = client_socket.recv(file_size - len(received_data))
                if not chunk:
                    break
                received_data += chunk
            
            # Write to file
            with open(filepath, 'wb') as f:
                f.write(received_data)
            
            if len(received_data) == file_size:
                print(f"{Colors.GREEN}File uploaded successfully: {filename}{Colors.RESET}")
                self.refresh_file_list()
            else:
                print(f"{Colors.RED}File upload incomplete: {len(received_data)}/{file_size} bytes{Colors.RESET}")
                if os.path.exists(filepath):
                    os.remove(filepath)
        
        except Exception as e:
            print(f"{Colors.RED}Error receiving file: {e}{Colors.RESET}")

    def stop_server(self):
        """Stop the server and close all connections"""
        self.running = False
        if self.socket:
            self.socket.close()
        for client_socket, _ in self.clients:
            client_socket.close()
        self.clients.clear()
        print(f"{Colors.YELLOW}Server stopped{Colors.RESET}")

# Global server instance
server = None

def print_directory_contents(path):
    try:
        with os.scandir(path) as entries:
            for i, entry in enumerate(entries):
                if entry.is_file():
                    size = entry.stat().st_size
                    print(f"{Colors.GREEN}{i:2d}. {entry.name} ({size} bytes){Colors.RESET}")
                elif entry.is_dir():
                    print(f"{Colors.BLUE}Directory: {entry.name}{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Error accessing directory: {e}{Colors.RESET}")

def wait_for_commands():
    global server
    while True:
        command = input("Enter command: ").strip().lower()
        if command == "show":
            print_directory_contents(shared_space)
        elif command == "exit":
            if server and server.running:
                server.stop_server()
            print("Exiting program.")
            sys.exit(0)
        elif command == "launch":
            if server and server.running:
                print(f"{Colors.YELLOW}Server is already running!{Colors.RESET}")
            else:
                print("Launching server...")
                server = Server()
                server.set_shared_space(shared_space)
                if not server.start_server():
                    server = None
        elif command == "stop":
            if server and server.running:
                server.stop_server()
                server = None
            else:
                print(f"{Colors.YELLOW}No server is currently running.{Colors.RESET}")
        elif command == "status":
            if server and server.running:
                print(f"{Colors.GREEN}Server is running on port {server.port}{Colors.RESET}")
                print(f"{Colors.CYAN}Connected clients: {len(server.clients)}{Colors.RESET}")
                print(f"{Colors.CYAN}Shared space: {shared_space}{Colors.RESET}")
                print(f"{Colors.CYAN}Files available: {len(server.file_list)}{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}Server is not running.{Colors.RESET}")
        elif command == "refresh":
            if server:
                server.refresh_file_list()
                print(f"{Colors.GREEN}File list refreshed. {len(server.file_list)} files available.{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}Server not running.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Unknown command: {command}{Colors.RESET}")

# Main program
shared_space = input("Shared space directory: ").strip()
if not shared_space:
    print("No directory entered.")
else:
    print(f"Shared space directory set to: {Colors.MAGENTA}{shared_space}{Colors.RESET}")
    print(f"Exists on disk: {Colors.MAGENTA}{os.path.exists(shared_space)}{Colors.RESET}")

    print("Available commands:")
    print(" show - Show directory contents")
    print(" launch - Start the server")
    print(" stop - Stop the server")
    print(" status - Check server status")
    print(" refresh - Refresh file list")
    print(" exit - Exit the program")

    wait_for_commands()