import socket
import threading
import sys
import json
from datetime import datetime
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import platform
import ctypes

class Client:
    def __init__(self, gui_callback=None):
        self.socket = None
        self.connected = False
        self.host = None
        self.port = None
        self.download_dir = "downloads"
        self.file_list = []
        self.gui_callback = gui_callback
        self.connection_timeout = 5
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def connect(self, host, port=8888):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.connection_timeout)
            
            if self.gui_callback:
                self.gui_callback("log", f"Connecting to {host}:{port}...", "info")
            
            self.socket.connect((host, port))
            self.socket.settimeout(2.0)
            
            self.connected = True
            self.host = host
            self.port = port
            
            if self.gui_callback:
                self.gui_callback("status", f"Connected to {host}:{port}")
                self.gui_callback("log", f"Connected to server", "success")
            
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()
            
            return True
            
        except Exception as e:
            error_msg = f"Connection failed: {e}"
            if self.gui_callback:
                self.gui_callback("status", "Disconnected")
                self.gui_callback("log", error_msg, "error")
            return False
    
    def listen_for_messages(self):
        """Listen for messages from server"""
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(16384).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                
                # Process complete JSON objects
                while buffer:
                    if buffer.startswith('{'):
                        brace_count = 0
                        json_end = -1
                        
                        for i, char in enumerate(buffer):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            json_str = buffer[:json_end]
                            buffer = buffer[json_end:]
                            self.process_json_message(json_str)
                            continue
                    
                    if '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            self.process_text_message(line.strip())
                    else:
                        break
                        
            except socket.timeout:
                continue
            except Exception as e:
                if self.connected:
                    self.gui_callback("log", f"Connection error: {e}", "error")
                break
        
        if self.connected:
            self.disconnect()
    
    def process_json_message(self, json_str):
        """Process JSON message from server"""
        try:
            data = json.loads(json_str)
            msg_type = data.get('type')
            
            if msg_type == 'file_list':
                files = data.get('files', [])
                self.file_list = files
                if self.gui_callback:
                    self.gui_callback("file_list", files)
                    self.gui_callback("log", f"File list updated: {len(files)} files", "success")
            
            elif msg_type == 'file_info':
                if self.gui_callback:
                    self.gui_callback("file_info", data)
            
            elif msg_type == 'file_transfer':
                self.receive_file_with_progress(data)
            
        except json.JSONDecodeError:
            pass
    
    def process_text_message(self, message):
        """Process text message from server"""
        if message.startswith("ERROR:"):
            self.gui_callback("log", message, "error")
        elif message.startswith("Server received:"):
            pass  # Don't log regular server acknowledgments
        else:
            self.gui_callback("log", f"Server: {message}", "server")
    
    def send_command(self, command):
        """Send command to server"""
        if not self.connected:
            self.gui_callback("log", "Not connected to server", "error")
            return False
        
        try:
            self.socket.send(command.encode('utf-8'))
            return True
        except Exception as e:
            self.gui_callback("log", f"Send error: {e}", "error")
            self.connected = False
            self.gui_callback("status", "Disconnected")
            return False
    
    def list_files(self):
        """Request file list from server"""
        return self.send_command("LIST_FILES")
    
    def get_file_info(self, file_index):
        """Request file information"""
        return self.send_command(f"FILE_INFO {file_index}")
    
    def download_file(self, file_index):
        """Request file download"""
        self.gui_callback("log", f"Downloading file...", "info")
        return self.send_command(f"GET_FILE {file_index}")
    
    def upload_file(self, filepath):
        """Upload file to server"""
        if not os.path.exists(filepath):
            self.gui_callback("log", f"File not found: {filepath}", "error")
            return False
        
        try:
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath)
            
            self.gui_callback("log", f"Uploading: {filename}", "info")
            self.gui_callback("upload_start", {
                'filename': filename,
                'size': file_size
            })
            
            upload_command = f"UPLOAD:{filename}:{file_size}"
            self.socket.send(upload_command.encode('utf-8'))
            time.sleep(0.1)
            
            sent_size = 0
            start_time = time.time()
            chunk_size = 65536
            
            with open(filepath, 'rb') as f:
                while sent_size < file_size:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    self.socket.sendall(chunk)
                    sent_size += len(chunk)
                    
                    progress = sent_size / file_size
                    elapsed = time.time() - start_time
                    speed = sent_size / elapsed if elapsed > 0 else 0
                    
                    self.gui_callback("upload_progress", {
                        'progress': progress,
                        'sent_size': sent_size,
                        'total_size': file_size,
                        'speed': speed,
                        'eta': (file_size - sent_size) / speed if speed > 0 else 0
                    })
            
            total_time = time.time() - start_time
            self.gui_callback("upload_complete", {
                'filename': filename,
                'total_time': total_time
            })
            self.gui_callback("log", f"Upload complete", "success")
            
            return True
            
        except Exception as e:
            self.gui_callback("log", f"Upload failed: {e}", "error")
            return False
    
    def receive_file_with_progress(self, file_info):
        """Receive file from server"""
        try:
            filename = file_info['name']
            file_size = file_info['size']
            filepath = os.path.join(self.download_dir, filename)
            
            self.gui_callback("log", f"Downloading: {filename}", "info")
            self.gui_callback("download_start", {
                'filename': filename,
                'size': file_size
            })
            
            self.socket.send("READY".encode('utf-8'))
            
            received_size = 0
            start_time = time.time()
            
            with open(filepath, 'wb') as f:
                while received_size < file_size:
                    remaining = file_size - received_size
                    chunk_size = min(65536, remaining)
                    
                    chunk = self.socket.recv(chunk_size)
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    received_size += len(chunk)
                    
                    progress = received_size / file_size
                    elapsed = time.time() - start_time
                    speed = received_size / elapsed if elapsed > 0 else 0
                    
                    self.gui_callback("download_progress", {
                        'progress': progress,
                        'received_size': received_size,
                        'total_size': file_size,
                        'speed': speed,
                        'eta': (file_size - received_size) / speed if speed > 0 else 0
                    })
            
            if received_size == file_size:
                total_time = time.time() - start_time
                self.gui_callback("download_complete", {
                    'filename': filename,
                    'total_time': total_time
                })
                self.gui_callback("log", f"Download complete", "success")
            else:
                self.gui_callback("log", f"Download incomplete", "error")
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
        except Exception as e:
            self.gui_callback("log", f"Download failed: {e}", "error")
    
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
    
    def disconnect(self):
        """Disconnect from server"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.gui_callback:
            self.gui_callback("status", "Disconnected")
            self.gui_callback("log", "Disconnected from server", "info")


class ClientGUI:
    def __init__(self, root):
        self.set_dpi_awareness()
        self.root = root
        self.client = Client(gui_callback=self.gui_callback)
        self.setup_ui()
    
    def set_dpi_awareness(self):
        """Set DPI awareness for clear rendering"""
        if os.name == 'nt':
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except:
                    pass
    
    def setup_styles(self):
        """Setup dark purple theme styles"""
        style = ttk.Style()
        
        # Use clam theme for better customization
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        
        # Purple dark theme color scheme based on the image
        self.colors = {
            'bg': '#000000',           # Pure black background
            'bg_secondary': '#141414', # Dark gray for secondary backgrounds
            'border': '#282828',       # Medium gray for borders
            'text_primary': '#ffffff', # White for primary text
            'text_secondary': '#a0a0a0', # Light gray for secondary text
            'accent': '#320064',       # Deep purple for accents
            'accent_hover': '#230046', # Darker purple for hover states
            'success': '#34c759',      # Keep green for success (stands out well)
            'error': '#ff3b30',        # Keep red for errors (stands out well)
            'warning': '#ff9500'       # Keep orange for warnings
        }
        
        # Configure base styles
        style.configure('.', 
                       background=self.colors['bg'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       focuscolor='')
        
        # Frame styles
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('Secondary.TFrame', background=self.colors['bg_secondary'])
        
        # Label styles
        style.configure('TLabel', 
                       background=self.colors['bg'],
                       foreground=self.colors['text_primary'],
                       font=('SF Pro Text', 10))
        
        style.configure('Title.TLabel',
                       font=('SF Pro Display', 20, 'bold'),
                       foreground=self.colors['text_primary'])
        
        style.configure('Subtitle.TLabel',
                       font=('SF Pro Text', 13),
                       foreground=self.colors['text_secondary'])
        
        style.configure('Caption.TLabel',
                       font=('SF Pro Text', 11),
                       foreground=self.colors['text_secondary'])
        
        # Button styles
        style.configure('TButton',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       focuscolor='',
                       font=('SF Pro Text', 11))
        
        style.configure('Accent.TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       focuscolor='',
                       font=('SF Pro Text', 11, 'bold'))
        
        style.map('Accent.TButton',
                 background=[('active', self.colors['accent_hover']),
                           ('pressed', self.colors['accent_hover'])])
        
        style.configure('Action.TButton',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       focuscolor='',
                       font=('SF Pro Text', 11))
        
        # Entry styles
        style.configure('TEntry',
                       fieldbackground=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=1,
                       relief='flat',
                       font=('SF Pro Text', 11))
        
        style.map('TEntry',
                 bordercolor=[('focus', self.colors['accent']),
                            ('!focus', self.colors['border'])])
        
        # LabelFrame styles
        style.configure('TLabelframe',
                       background=self.colors['bg'],
                       borderwidth=0)
        
        style.configure('TLabelframe.Label',
                       background=self.colors['bg'],
                       foreground=self.colors['text_primary'],
                       font=('SF Pro Text', 12, 'bold'))
        
        # Treeview styles (File list)
        style.configure('Treeview',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       fieldbackground=self.colors['bg_secondary'],
                       borderwidth=0,
                       font=('SF Pro Text', 11))
        
        style.configure('Treeview.Heading',
                       background=self.colors['accent'],
                       foreground=self.colors['text_primary'],
                       borderwidth=0,
                       relief='flat',
                       font=('SF Pro Text', 11, 'bold'))
        
        style.map('Treeview',
                 background=[('selected', self.colors['accent_hover'])],
                 foreground=[('selected', self.colors['text_primary'])])
        
        # Progressbar styles
        style.configure("Horizontal.TProgressbar",
                       background=self.colors['accent'],
                       troughcolor=self.colors['bg_secondary'],
                       borderwidth=0,
                       lightcolor=self.colors['accent'],
                       darkcolor=self.colors['accent'])

    def setup_ui(self):
        """Setup the dark purple themed UI"""
        # Ensure styles/colors are initialized before using them
        self.setup_styles()

        self.root.title("File Transfer - Dark Purple Theme")
        self.root.geometry("900x650")
        self.root.configure(bg=self.colors['bg'])
        self.root.minsize(800, 600)
        
        # Main container with subtle padding
        main_container = ttk.Frame(self.root, padding="0")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Header with app title
        header_frame = ttk.Frame(main_container, style='Secondary.TFrame', padding=(20, 15, 20, 15))
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=0, pady=(0, 1))
        header_frame.columnconfigure(1, weight=1)
        
        ttk.Label(header_frame, text="File Transfer", style='Title.TLabel').grid(row=0, column=0, sticky=tk.W)
        
        status_frame = ttk.Frame(header_frame, style='Secondary.TFrame')
        status_frame.grid(row=0, column=1, sticky=tk.E)
        
        self.status_indicator = ttk.Label(status_frame, text="●", foreground=self.colors['text_secondary'], 
                                         font=('SF Pro Text', 9), style='TLabel')
        self.status_indicator.grid(row=0, column=0, padx=(0, 8))
        
        self.status_label = ttk.Label(status_frame, text="Disconnected", style='Caption.TLabel')
        self.status_label.grid(row=0, column=1)
        
        # Main content area
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(1, weight=1)
        
        # Left sidebar - Connection panel
        sidebar_frame = ttk.Frame(content_frame, style='Secondary.TFrame', padding=20)
        sidebar_frame.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 15))
        sidebar_frame.columnconfigure(0, weight=1)
        
        ttk.Label(sidebar_frame, text="Connection", style='Subtitle.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 15))
        
        # Connection form
        form_frame = ttk.Frame(sidebar_frame, style='Secondary.TFrame')
        form_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(form_frame, text="Host", style='Caption.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.host_entry = ttk.Entry(form_frame, width=16, font=('SF Pro Text', 12))
        self.host_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        self.host_entry.insert(0, "localhost")
        
        ttk.Label(form_frame, text="Port", style='Caption.TLabel').grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.port_entry = ttk.Entry(form_frame, width=8, font=('SF Pro Text', 12))
        self.port_entry.grid(row=3, column=0, sticky=tk.W, pady=(0, 20))
        self.port_entry.insert(0, "8888")
        
        self.connect_btn = ttk.Button(form_frame, text="Connect", command=self.connect_server, 
                                     style='Accent.TButton', width=12)
        self.connect_btn.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        
        self.disconnect_btn = ttk.Button(form_frame, text="Disconnect", command=self.disconnect_server, 
                                        style='Action.TButton', width=12, state='disabled')
        self.disconnect_btn.grid(row=5, column=0, sticky=(tk.W, tk.E))
        
        # Right panel - File operations
        files_frame = ttk.LabelFrame(content_frame, text="Server Files", padding=15)
        files_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(1, weight=1)
        
        # File list with custom styling
        file_list_container = ttk.Frame(files_frame, relief='flat', borderwidth=1)
        file_list_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        file_list_container.columnconfigure(0, weight=1)
        file_list_container.rowconfigure(0, weight=1)
        
        # File treeview
        columns = ('name', 'size', 'modified')
        self.file_tree = ttk.Treeview(file_list_container, columns=columns, show='headings', height=8)
        self.file_tree.heading('name', text='Name')
        self.file_tree.heading('size', text='Size')
        self.file_tree.heading('modified', text='Modified')
        self.file_tree.column('name', width=200, minwidth=150)
        self.file_tree.column('size', width=80, minwidth=60)
        self.file_tree.column('modified', width=120, minwidth=100)
        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for file tree
        scrollbar = ttk.Scrollbar(file_list_container, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # File action buttons
        action_frame = ttk.Frame(files_frame)
        action_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        
        self.refresh_btn = ttk.Button(action_frame, text="Refresh", command=self.refresh_files, 
                                     style='Action.TButton', state='disabled')
        self.refresh_btn.grid(row=0, column=0, padx=(0, 8))
        
        self.download_btn = ttk.Button(action_frame, text="Download", command=self.download_file, 
                                      style='Action.TButton', state='disabled')
        self.download_btn.grid(row=0, column=1, padx=8)
        
        self.upload_btn = ttk.Button(action_frame, text="Upload", command=self.upload_file, 
                                    style='Action.TButton', state='disabled')
        self.upload_btn.grid(row=0, column=2, padx=8)
        
        # Progress area
        progress_frame = ttk.Frame(content_frame)
        progress_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)
        
        self.upload_label = ttk.Label(progress_frame, text="", style='Caption.TLabel')
        self.upload_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.upload_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.upload_progress.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.download_label = ttk.Label(progress_frame, text="", style='Caption.TLabel')
        self.download_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.download_progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.download_progress.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        # Activity log
        log_frame = ttk.LabelFrame(content_frame, text="Activity", padding=15)
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(15, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        log_container = ttk.Frame(log_frame, relief='flat', borderwidth=1)
        log_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_container.columnconfigure(0, weight=1)
        log_container.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_container, height=6, bg=self.colors['bg_secondary'], 
                                                 fg=self.colors['text_primary'], borderwidth=0,
                                                 font=('SF Mono', 9), wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure weights for expansion
        content_frame.rowconfigure(2, weight=1)
        files_frame.rowconfigure(1, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Bind events
        self.file_tree.bind('<Double-1>', lambda e: self.show_file_info())
        
        # Initialize
        self.update_log_tags()
        self.log("Ready to connect", "info")
    
    def update_log_tags(self):
        """Update log text tags with colors (do not remove built-in tags)"""
        # Configure or create the tags we use without deleting other tags
        self.log_text.tag_config("info", foreground=self.colors['text_secondary'])
        self.log_text.tag_config("success", foreground=self.colors['success'])
        self.log_text.tag_config("error", foreground=self.colors['error'])
        self.log_text.tag_config("server", foreground=self.colors['accent'])
    
    def gui_callback(self, callback_type, data, log_type=None):
        """Handle callbacks from client"""
        if callback_type == "log":
            self.log(data, log_type)
        elif callback_type == "status":
            self.update_status(data)
        elif callback_type == "file_list":
            self.update_file_list(data)
        elif callback_type == "file_info":
            self.show_file_info_dialog(data)
        elif callback_type in ["upload_start", "upload_progress", "upload_complete", 
                              "download_start", "download_progress", "download_complete"]:
            self.update_progress(callback_type, data)
    
    def log(self, message, log_type="info"):
        """Add message to log with clean formatting"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"
        
        # Capture start index before inserting, then tag inserted range
        start_index = self.log_text.index("end-1c")
        self.log_text.insert(tk.END, formatted)
        end_index = self.log_text.index("end-1c")
        
        # Add tag for the newly inserted text
        try:
            self.log_text.tag_add(log_type, start_index, end_index)
        except Exception:
            pass
        
        self.log_text.see(tk.END)
    
    def update_status(self, status):
        """Update connection status with visual indicator"""
        self.status_label.config(text=status)
        
        if status.startswith("Connected"):
            color = self.colors['success']
            self.status_indicator.config(foreground=color)
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.refresh_btn.config(state='normal')
            self.download_btn.config(state='normal')
            self.upload_btn.config(state='normal')
        else:
            color = self.colors['text_secondary']
            self.status_indicator.config(foreground=color)
            self.connect_btn.config(state='normal')
            self.disconnect_btn.config(state='disabled')
            self.refresh_btn.config(state='disabled')
            self.download_btn.config(state='disabled')
            self.upload_btn.config(state='disabled')
    
    def update_file_list(self, file_list):
        """Update file list in treeview"""
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        for i, file_info in enumerate(file_list):
            name = file_info['name']
            size = self.client.format_file_size(file_info['size'])
            modified = datetime.fromtimestamp(file_info['modified']).strftime('%m/%d/%Y %H:%M')
            self.file_tree.insert('', 'end', values=(name, size, modified), tags=(str(i),))
    
    def update_progress(self, callback_type, data):
        """Update progress bars with clean labels"""
        if callback_type == "upload_start":
            self.upload_progress['value'] = 0
            self.upload_label.config(text=f"Uploading {data['filename']}")
        elif callback_type == "upload_progress":
            self.upload_progress['value'] = data['progress'] * 100
        elif callback_type == "upload_complete":
            self.upload_progress['value'] = 100
            self.upload_label.config(text="Upload complete")
        
        elif callback_type == "download_start":
            self.download_progress['value'] = 0
            self.download_label.config(text=f"Downloading {data['filename']}")
        elif callback_type == "download_progress":
            self.download_progress['value'] = data['progress'] * 100
        elif callback_type == "download_complete":
            self.download_progress['value'] = 100
            self.download_label.config(text="Download complete")
    
    def connect_server(self):
        """Connect to server"""
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        
        if not host:
            messagebox.showerror("Error", "Please enter host address")
            return
        
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return
        
        self.connect_btn.config(state='disabled')
        self.log(f"Connecting to {host}:{port}...")
        
        def connect_thread():
            success = self.client.connect(host, port)
            if not success:
                self.root.after(0, lambda: self.connect_btn.config(state='normal'))
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def disconnect_server(self):
        """Disconnect from server"""
        self.client.disconnect()
    
    def refresh_files(self):
        """Refresh file list"""
        if self.client.connected:
            self.client.list_files()
        else:
            messagebox.showerror("Error", "Not connected to server")
    
    def show_file_info(self):
        """Show file information on double-click"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        item = self.file_tree.item(selection[0])
        tags = item['tags']
        if tags:
            file_index = int(tags[0])
            self.client.get_file_info(file_index)
    
    def show_file_info_dialog(self, file_info):
        """Show file info in a clean dialog"""
        info_window = tk.Toplevel(self.root)
        info_window.title("File Information")
        info_window.geometry("400x220")
        info_window.configure(bg=self.colors['bg'])
        info_window.transient(self.root)
        info_window.resizable(False, False)
        
        # Center the window
        info_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - info_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - info_window.winfo_height()) // 2
        info_window.geometry(f"+{x}+{y}")
        
        info_frame = ttk.Frame(info_window, padding=25)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(info_frame, text="File Information", style='Subtitle.TLabel').pack(pady=(0, 20))
        
        info_text = f"Name: {file_info['name']}\n\nSize: {self.client.format_file_size(file_info['size'])}\n\nModified: {datetime.fromtimestamp(file_info['modified']).strftime('%B %d, %Y at %H:%M')}"
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, style='TLabel').pack(anchor=tk.W)
        
        ttk.Button(info_frame, text="Close", command=info_window.destroy, 
                  style='Action.TButton', width=10).pack(pady=(25, 0))
    
    def download_file(self):
        """Download selected file"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file first")
            return
        
        item = self.file_tree.item(selection[0])
        tags = item['tags']
        if tags:
            file_index = int(tags[0])
            self.client.download_file(file_index)
    
    def upload_file(self):
        """Upload file with clean file dialog"""
        if not self.client.connected:
            messagebox.showerror("Error", "Not connected to server")
            return
        
        filepath = filedialog.askopenfilename(
            title="Select file to upload",
            filetypes=[("All files", "*.*")]
        )
        
        if filepath:
            threading.Thread(target=self.client.upload_file, args=(filepath,), daemon=True).start()


def main():
    """Main function"""
    root = tk.Tk()
    try:
        if platform.system() == "Windows":
            root.iconbitmap("client_icon.ico")
    except:
        pass
    
    # Set window class for better window manager integration
    try:
        root.createcommand('tk::mac::ShowPreferences', lambda: None)
    except:
        pass
    
    app = ClientGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
