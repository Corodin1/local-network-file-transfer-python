# Local Network File Transfer

A modern, GUI-based file transfer application for local networks with an Apple-inspired design.
Features

Modern GUI: Beautiful dark theme with rounded corners and smooth animations

Easy File Transfers: Drag-and-drop style interface for uploading and downloading

Real-time Progress: Live progress bars with speed and ETA information

Cross-platform: Works on Windows, macOS, and Linux

No Installation Required: Portable executable available

## Quick Start
## Server Setup

Run server.py on the machine you want to use as the server

Enter the path to the folder you want to share when prompted

Type launch to start the server

Note the displayed IP address and port (default: 8888)

## Client Setup

Run client.py or client.exe on the client machine
Enter the server's IP address and port in the connection panel

Click "Connect" to establish connection

Use the intuitive GUI to browse, upload, and download files

## Server Commands

## Once server.py is running, you can use these commands in the server console:

show - Display directory contents

launch - Start the server

stop - Stop the server

status - Check server status

refresh - Refresh file list

exit - Exit the program

## Client Features
## Connection Panel

Host: Server IP address (default: localhost)

Port: Server port (default: 8888)

Connect/Disconnect: One-click connection management
Status Indicator: Visual connection status

## File Operations

Refresh List: Update the file list from the server
File Info: Double-click any file to view detailed information

Download: Select a file and click "Download"

Upload: Click "Upload" to select and send files to the server

## Progress Tracking

Real-time upload and download progress bars

Transfer speed and ETA display

Visual completion indicators

## Activity Log

Timestamped operation history

Color-coded messages (success, error, info)

Auto-scrolling to latest activity

## Important Notes

Files Only: The system transfers individual files, not folders
Large Files: For large files or folders, compress them to .zip or .rar first

Downloads: All downloaded files are saved in the downloads folder

Network: Ensure both machines are on the same local network

## System Requirements

Python 3.8+ (for .py version)

Windows 7+ / macOS 10.12+ / Linux (for .exe version)

Network connectivity between machines

## Troubleshooting

Connection Issues: Verify IP address and check firewall settings

File Not Found: Ensure the shared directory exists on the server
Permission Errors: Check file/folder permissions on both machines

## Version Information

## Current version features a complete GUI overhaul with:

CustomTkinter-based modern interface

Apple-inspired dark theme design

Rounded corners and smooth animations

Hover effects and visual feedback

Professional layout and spacing
