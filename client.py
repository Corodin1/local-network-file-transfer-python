import socket
import threading
import sys
import json
from datetime import datetime
import os
import time

class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    WHITE = '\033[37m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

class Client:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.host = None
        self.port = None
        self.download_dir = "downloads"
        self.file_list = []
        
        # Create downloads directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def connect(self, host, port=8888):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Optimize socket settings
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.socket.connect((host, port))
            self.connected = True
            self.host = host
            self.port = port
            
            print(f"{Colors.GREEN}Connected to server at {host}:{port}{Colors.RESET}")
            
            # Start listening for messages from server
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Failed to connect to server: {e}{Colors.RESET}")
            return False
    
    def listen_for_messages(self):
        """Listen for incoming messages from the server"""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                # Check if it's a JSON response
                if data.startswith('{'):
                    try:
                        response_data = json.loads(data)
                        if response_data.get('type') == 'file_list':
                            self.file_list = response_data['files']
                            self.display_file_list()
                        elif response_data.get('type') == 'file_info':
                            self.display_file_info(response_data)
                        elif response_data.get('type') == 'file_transfer':
                            self.receive_file_with_progress(response_data)
                        continue
                    except json.JSONDecodeError:
                        pass
                
                # Regular messages
                if data.startswith("ERROR:"):
                    print(f"{Colors.RED}{data}{Colors.RESET}")
                    print("Enter command: ", end="", flush=True)
                elif data.startswith("Server received:"):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"\n{Colors.CYAN}[{timestamp}] {data}{Colors.RESET}")
                    print("Enter command: ", end="", flush=True)
                else:
                    print(f"\n{Colors.CYAN}Server: {Colors.WHITE}{data}{Colors.RESET}")
                    print("Enter command: ", end="", flush=True)
                
            except Exception as e:
                if self.connected:
                    print(f"{Colors.RED}Error receiving message: {e}{Colors.RESET}")
                break
    
    def display_file_list(self):
        """Display the list of files from server"""
        print(f"\n{Colors.CYAN}╔{'═' * 60}╗{Colors.RESET}")
        print(f"{Colors.CYAN}║ {Colors.YELLOW}Files in shared directory ({len(self.file_list)} files):{Colors.CYAN} {' ' * 20}║{Colors.RESET}")
        print(f"{Colors.CYAN}╠{'═' * 60}╣{Colors.RESET}")
        
        if not self.file_list:
            print(f"{Colors.CYAN}║ {Colors.RED}No files found{' ' * 45}║{Colors.RESET}")
        else:
            for i, file_info in enumerate(self.file_list):
                name = file_info['name']
                size = self.format_file_size(file_info['size'])
                modified = datetime.fromtimestamp(file_info['modified']).strftime('%Y-%m-%d %H:%M')
                
                print(f"{Colors.CYAN}║ {Colors.WHITE}{i:2d}. {Colors.GREEN}{name:<25} {Colors.BLUE}{size:>10} {Colors.MAGENTA}{modified}{Colors.CYAN} ║{Colors.RESET}")
        
        print(f"{Colors.CYAN}╚{'═' * 60}╝{Colors.RESET}")
        print("Enter command: ", end="", flush=True)
    
    def display_file_info(self, file_info):
        """Display detailed information about a file"""
        print(f"\n{Colors.CYAN}╔{'═' * 50}╗{Colors.RESET}")
        print(f"{Colors.CYAN}║ {Colors.YELLOW}File Information:{Colors.CYAN} {' ' * 32}║{Colors.RESET}")
        print(f"{Colors.CYAN}╠{'═' * 50}╣{Colors.RESET}")
        print(f"{Colors.CYAN}║ {Colors.GREEN}Index: {Colors.WHITE}{file_info['index']}{Colors.CYAN} {' ' * 39}║{Colors.RESET}")
        print(f"{Colors.CYAN}║ {Colors.GREEN}Name: {Colors.WHITE}{file_info['name']}{Colors.CYAN} {' ' * (38 - len(file_info['name']))}║{Colors.RESET}")
        print(f"{Colors.CYAN}║ {Colors.GREEN}Size: {Colors.BLUE}{self.format_file_size(file_info['size'])}{Colors.CYAN} {' ' * 32}║{Colors.RESET}")
        modified = datetime.fromtimestamp(file_info['modified']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{Colors.CYAN}║ {Colors.GREEN}Modified: {Colors.MAGENTA}{modified}{Colors.CYAN} ║{Colors.RESET}")
        readable = "Yes" if file_info.get('readable', True) else "No"
        print(f"{Colors.CYAN}║ {Colors.GREEN}Readable: {Colors.WHITE}{readable}{Colors.CYAN} {' ' * 37}║{Colors.RESET}")
        print(f"{Colors.CYAN}╚{'═' * 50}╝{Colors.RESET}")
        print("Enter command: ", end="", flush=True)
    
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def draw_progress_bar(self, progress, width=40):
        """Draw a progress bar"""
        filled = int(width * progress)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {progress:.1%}"
    
    def send_command(self, command):
        """Send a command to the server"""
        if not self.connected:
            print(f"{Colors.RED}Not connected to server{Colors.RESET}")
            return False
        
        try:
            self.socket.send(command.encode('utf-8'))
            return True
        except Exception as e:
            print(f"{Colors.RED}Failed to send command: {e}{Colors.RESET}")
            self.connected = False
            return False
    
    def list_files(self):
        """Request file list from server"""
        return self.send_command("LIST_FILES")
    
    def get_file_info(self, file_index):
        """Request file information from server by index"""
        return self.send_command(f"FILE_INFO {file_index}")
    
    def download_file(self, file_index):
        """Request to download a file from server by index"""
        return self.send_command(f"GET_FILE {file_index}")
    
    def upload_file_with_progress(self, filepath):
        """Upload a file to the server"""
        if not os.path.exists(filepath):
            print(f"{Colors.RED}File not found: {filepath}{Colors.RESET}")
            return False
        
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            print(f"{Colors.YELLOW}Uploading: {filename} ({self.format_file_size(file_size)}){Colors.RESET}")
            
            # Send upload command
            upload_command = f"UPLOAD:{filename}:{file_size}"
            self.socket.send(upload_command.encode('utf-8'))
            
            # Wait for server to be ready
            time.sleep(0.05)
            
            # Upload file in chunks
            chunk_size = 65536  # 64KB chunks
            sent_size = 0
            start_time = time.time()
            last_update_time = start_time
            last_sent_size = 0
            
            with open(filepath, 'rb') as f:
                while sent_size < file_size:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    self.socket.sendall(chunk)
                    sent_size += len(chunk)
                    
                    # Update progress every 100ms
                    current_time = time.time()
                    if current_time - last_update_time >= 0.1:
                        progress = sent_size / file_size
                        time_diff = current_time - last_update_time
                        size_diff = sent_size - last_sent_size
                        instant_speed = size_diff / time_diff if time_diff > 0 else 0
                        
                        if instant_speed > 0:
                            eta = (file_size - sent_size) / instant_speed
                        else:
                            eta = 0
                        
                        print(f"\r{Colors.CYAN}{self.draw_progress_bar(progress)} "
                              f"{Colors.YELLOW}{self.format_file_size(sent_size)}/{self.format_file_size(file_size)} "
                              f"{Colors.MAGENTA}{self.format_file_size(instant_speed)}/s "
                              f"{Colors.BLUE}ETA: {eta:.1f}s{Colors.RESET}", end="", flush=True)
                        
                        last_update_time = current_time
                        last_sent_size = sent_size
            
            total_time = time.time() - start_time
            average_speed = file_size / total_time if total_time > 0 else 0
            
            print(f"\r{Colors.GREEN}✓ Upload complete: {filename} "
                  f"{Colors.CYAN}({self.format_file_size(file_size)}) "
                  f"{Colors.MAGENTA}in {total_time:.1f}s "
                  f"({self.format_file_size(average_speed)}/s avg){Colors.RESET}")
            print("Enter command: ", end="", flush=True)
            return True
            
        except Exception as e:
            print(f"\n{Colors.RED}✗ Upload failed: {e}{Colors.RESET}")
            print("Enter command: ", end="", flush=True)
            return False
    
    def receive_file_with_progress(self, file_info):
        """Receive a file from the server with stable speeds"""
        try:
            filename = file_info['name']
            file_size = file_info['size']
            filepath = os.path.join(self.download_dir, filename)
            
            print(f"{Colors.YELLOW}Downloading: {filename} ({self.format_file_size(file_size)}){Colors.RESET}")
            
            # Send acknowledgment
            self.socket.send("READY".encode('utf-8'))
            
            # SIMPLE AND STABLE DOWNLOAD APPROACH
            received_size = 0
            start_time = time.time()
            last_update_time = start_time
            last_received_size = 0
            
            # Use a reasonable buffer size
            buffer_size = 65536  # 64KB
            
            with open(filepath, 'wb') as f:
                while received_size < file_size:
                    # Calculate remaining bytes
                    remaining = file_size - received_size
                    chunk_size = min(buffer_size, remaining)
                    
                    # Receive chunk
                    chunk = self.socket.recv(chunk_size)
                    if not chunk:
                        break
                    
                    # Write to file immediately
                    f.write(chunk)
                    received_size += len(chunk)
                    
                    # Update progress every 100ms (not too frequent)
                    current_time = time.time()
                    if current_time - last_update_time >= 0.1:
                        progress = received_size / file_size
                        time_diff = current_time - last_update_time
                        size_diff = received_size - last_received_size
                        instant_speed = size_diff / time_diff if time_diff > 0 else 0
                        
                        if instant_speed > 0:
                            eta = (file_size - received_size) / instant_speed
                        else:
                            eta = 0
                        
                        print(f"\r{Colors.CYAN}{self.draw_progress_bar(progress)} "
                              f"{Colors.YELLOW}{self.format_file_size(received_size)}/{self.format_file_size(file_size)} "
                              f"{Colors.MAGENTA}{self.format_file_size(instant_speed)}/s "
                              f"{Colors.BLUE}ETA: {eta:.1f}s{Colors.RESET}", end="", flush=True)
                        
                        last_update_time = current_time
                        last_received_size = received_size
            
            total_time = time.time() - start_time
            average_speed = received_size / total_time if total_time > 0 else 0
            
            if received_size == file_size:
                print(f"\r{Colors.GREEN}✓ Download complete: {filename} "
                      f"{Colors.CYAN}({self.format_file_size(file_size)}) "
                      f"{Colors.MAGENTA}in {total_time:.1f}s "
                      f"({self.format_file_size(average_speed)}/s avg){Colors.RESET}")
            else:
                print(f"\r{Colors.RED}✗ Download incomplete: {received_size}/{file_size} bytes{Colors.RESET}")
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            print("Enter command: ", end="", flush=True)
            
        except Exception as e:
            print(f"\n{Colors.RED}✗ Download failed: {e}{Colors.RESET}")
            print("Enter command: ", end="", flush=True)
    
    def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.socket:
            self.socket.close()
        print(f"{Colors.YELLOW}Disconnected from server{Colors.RESET}")

def print_help():
    """Print available commands"""
    print(f"\n{Colors.CYAN}Available commands:{Colors.RESET}")
    print(" connect [host] [port]    - Connect to server (port defaults to 8888)")
    print(" list                     - List files in server's shared directory")
    print(" info [index]             - Get information about a file by index")
    print(" download [index]         - Download a file from the server by index")
    print(" upload [filepath]        - Upload a file to the server")
    print(" send [message]           - Send a message to the server")
    print(" status                   - Show connection status")
    print(" disconnect               - Disconnect from server")
    print(" help                     - Show this help message")
    print(" exit                     - Exit the program")
    print(f"\n{Colors.YELLOW}Examples:{Colors.RESET}")
    print(" connect 192.168.1.100 8888")
    print(" list")
    print(" info 2")
    print(" download 1")
    print(" upload /path/to/myfile.txt")
    print(" send Hello Server!")
    print("")

def wait_for_commands():
    """Main command loop"""
    client = Client()
    
    print(f"{Colors.MAGENTA}Client started. Type 'help' for available commands.{Colors.RESET}")
    print(f"{Colors.MAGENTA}Downloads will be saved to: {client.download_dir}/{Colors.RESET}")
    
    while True:
        try:
            command_input = input("Enter command: ").strip()
            if not command_input:
                continue
            
            parts = command_input.split()
            command = parts[0].lower()
            
            if command == "exit":
                if client.connected:
                    client.disconnect()
                print("Exiting program.")
                break
                
            elif command == "help":
                print_help()
                
            elif command == "connect":
                if client.connected:
                    print(f"{Colors.YELLOW}Already connected to server. Disconnect first.{Colors.RESET}")
                    continue
                
                if len(parts) < 2:
                    print(f"{Colors.RED}Usage: connect [host] [port]{Colors.RESET}")
                    continue
                
                host = parts[1]
                port = 8888  # default port
                if len(parts) >= 3:
                    try:
                        port = int(parts[2])
                    except ValueError:
                        print(f"{Colors.RED}Invalid port number{Colors.RESET}")
                        continue
                
                print(f"{Colors.YELLOW}Connecting to {host}:{port}...{Colors.RESET}")
                client.connect(host, port)
                
            elif command == "disconnect":
                if client.connected:
                    client.disconnect()
                else:
                    print(f"{Colors.YELLOW}Not connected to any server.{Colors.RESET}")
                    
            elif command == "status":
                if client.connected:
                    print(f"{Colors.GREEN}Connected to {client.host}:{client.port}{Colors.RESET}")
                    print(f"{Colors.CYAN}Cached file list: {len(client.file_list)} files{Colors.RESET}")
                else:
                    print(f"{Colors.YELLOW}Not connected to any server.{Colors.RESET}")
                    
            elif command == "send":
                if not client.connected:
                    print(f"{Colors.RED}Not connected to server. Use 'connect' first.{Colors.RESET}")
                    continue
                
                if len(parts) < 2:
                    print(f"{Colors.RED}Usage: send [message]{Colors.RESET}")
                    continue
                
                message = ' '.join(parts[1:])
                if client.send_command(message):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"{Colors.GREEN}[{timestamp}] Sent: {Colors.WHITE}{message}{Colors.RESET}")
            
            elif command == "list":
                if not client.connected:
                    print(f"{Colors.RED}Not connected to server. Use 'connect' first.{Colors.RESET}")
                    continue
                
                if client.list_files():
                    print(f"{Colors.YELLOW}Requesting file list from server...{Colors.RESET}")
            
            elif command == "info":
                if not client.connected:
                    print(f"{Colors.RED}Not connected to server. Use 'connect' first.{Colors.RESET}")
                    continue
                
                if len(parts) < 2:
                    print(f"{Colors.RED}Usage: info [index]{Colors.RESET}")
                    continue
                
                try:
                    file_index = int(parts[1])
                    if client.get_file_info(file_index):
                        print(f"{Colors.YELLOW}Requesting info for file index: {file_index}{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Invalid file index. Must be a number.{Colors.RESET}")
            
            elif command == "download":
                if not client.connected:
                    print(f"{Colors.RED}Not connected to server. Use 'connect' first.{Colors.RESET}")
                    continue
                
                if len(parts) < 2:
                    print(f"{Colors.RED}Usage: download [index]{Colors.RESET}")
                    continue
                
                try:
                    file_index = int(parts[1])
                    if client.download_file(file_index):
                        print(f"{Colors.YELLOW}Requesting download for file index: {file_index}{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}Invalid file index. Must be a number.{Colors.RESET}")
            
            elif command == "upload":
                if not client.connected:
                    print(f"{Colors.RED}Not connected to server. Use 'connect' first.{Colors.RESET}")
                    continue
                
                if len(parts) < 2:
                    print(f"{Colors.RED}Usage: upload [filepath]{Colors.RESET}")
                    continue
                
                filepath = ' '.join(parts[1:])
                if client.upload_file_with_progress(filepath):
                    print(f"{Colors.GREEN}Upload initiated: {filepath}{Colors.RESET}")
                    
            else:
                print(f"{Colors.RED}Unknown command: {command}{Colors.RESET}")
                print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted by user{Colors.RESET}")
            if client.connected:
                client.disconnect()
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")

if __name__ == "__main__":
    print(f"{Colors.CYAN}Python Client for Local Network Server{Colors.RESET}")
    print(f"{Colors.CYAN}Python version: {sys.version.splitlines()[0]}{Colors.RESET}")
    
    wait_for_commands()