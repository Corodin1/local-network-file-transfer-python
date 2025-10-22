
# Local network file transfer

Launch the `server.py` file on your desired 'server' machine and launch `client.py` on your other machine.

Please note that you can only transfer files, no folders or subfolders. Use .zip or .rar if you want to transfer entire folders or large files.


## Server setup

Once server.py is launched you will have to choose a folder that will be used as your shared space/cloud

Copy the directory and paste it in the console.

To start the server use the launch command.

```launch```

The console will display the server IP and PORT, you will need those for setting up clients.

### Available server commands

``` show - Show directory contents
 launch - Start the server
 stop - Stop the server
 status - Check server status
 refresh - Refresh file list
 exit - Exit the program
``` 

## Client setup
Launch `client.py`or `client.exe` and run the connect command with your server IP and PORT

```connect 111.111.111.111 8888```

To upload or download files simply use the `download` command with the file index (use list command to show the files and their index) or `upload`commands + your file path, to make things easier you can place your file in the same directory as the program so you can just type your file name and extention.

Downloaded files will be placed in `downloads` folder in the same dir as your client file.

### Available client commands

```connect [host] [port]    - Connect to server (port defaults to 8888)
 list                     - List files in server's shared directory
 info [index]             - Get information about a file by index
 download [index]         - Download a file from the server by index
 upload [filepath]        - Upload a file to the server
 send [message]           - Send a message to the server
 status                   - Show connection status
 disconnect               - Disconnect from server
 help                     - Show this help message
 exit                     - Exit the program
 ```
