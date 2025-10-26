# C2 Server - Command and Control System

A minimalistic Command and Control (C2) simulation system for educational purposes and authorized security testing. The system consists of a Python server (command dispatcher) and Python client (agent) communicating via TCP sockets with a custom JSON-based protocol.


## Requirements

- Python 3.7 or higher
- No external dependencies (uses Python standard library only)

## Setup Instructions

1. Clone or download this repository
2. Verify Python installation:
   ```bash
   python --version
   ```

## Running the System

### Start the Server

Open a terminal and run:

```bash
python -m server.server
```

Or on Windows:

```bash
py -m server.server
```

The server will start listening on the configured host and port (default: `localhost:4444`).

### Start the Client

Open a separate terminal and run:

```bash
python -m client.client
```

Or with custom server connection details:

```bash
python -m client.client <host> <port>
```

**Examples:**
```bash
py -m client.client
py -m client.client localhost 4444
py -m client.client 192.168.1.100 8080
```

### Operator Interface Commands

Once the server is running and clients are connected, use these commands:

- `sessions` - List all connected clients
- `use <session_id>` - Switch to a specific client session
- `help` - Show available commands
- `exit` or `quit` - Shutdown server gracefully
- `<shell command>` - Send command to the active client (e.g., `whoami`, `pwd`, `ls`)

## Protocol Description

The system uses a **length-prefixed JSON protocol** over TCP for reliable message framing.

### Wire Format

```
[4-byte length (big-endian)][JSON payload (UTF-8)]
```

- **Length prefix**: 4 bytes encoding the JSON payload size (supports messages up to 4GB)
- **JSON payload**: UTF-8 encoded JSON message

### Message Types

**1. Registration (Client → Server)**
```json
{
  "type": "registration",
  "client_id": "hostname",
  "timestamp": "2025-10-27T14:30:00.123456",
  "auth_token": "secret_c2_token_12345"
}
```

**2. Command (Server → Client)**
```json
{
  "type": "command",
  "command": "whoami"
}
```

**3. Result (Client → Server)**
```json
{
  "type": "result",
  "command": "whoami",
  "stdout": "user\n",
  "stderr": "",
  "return_code": 0,
  "timestamp": "2025-10-27T14:30:05.654321"
}
```

## Features Implemented

### Level 1 - Basic Server & Client ✅

- TCP server listening on configurable port
- Client connection and registration with hostname
- Session management for operator commands
- Shell command execution on client
- Bidirectional communication (commands and results)
- Display of stdout, stderr, and return codes

### Level 2 - Comprehensive Logging ✅

- Dual logging system (console + file)
- Timestamped log entries
- Unique session IDs for each client
- Per-session log files (`logs/c2_server_SESSION-*.log`)
- Main server log (`logs/c2_server_MAIN_*.log`)
- Logged events:
  - Client connections and disconnections
  - Registration messages
  - Commands sent to clients
  - Results received from clients

### Level 3 - Multi-Client Support ✅

- Concurrent client connections (configurable limit, default: 50)
- Multi-threaded architecture:
  - Main thread for operator interface
  - Listener thread for accepting connections
  - Handler thread per client for command execution
- Thread-safe session management
- Operator can list all active sessions
- Session switching to send commands to specific clients
- Per-client command queues
- Graceful handling of client disconnects

### Level 4 - Encryption & Authentication ✅

- **TLS/SSL Encryption**: Secure communication using TLS (configurable)
- **Token-Based Authentication**: Shared secret token validation during registration
- Configuration flags in [common/config.py](common/config.py):
  - `TLS_ENABLED` - Enable/disable TLS encryption
  - `AUTH_ENABLED` - Enable/disable token authentication
  - `AUTH_TOKEN` - Shared authentication token

#### Enabling TLS Encryption

To use TLS encryption, you must first generate a server certificate and key:

**Generate self-signed certificate (for testing):**

```bash
# Using OpenSSLa
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes
```

When prompted, you can use default values or customize:
- Common Name (CN): Use your server's hostname or IP address
- Other fields: Can be left as default for testing

**Enable TLS in configuration:**

1. Place `server.crt` and `server.key` in the project root directory
2. Edit [common/config.py](common/config.py):
   ```python
   TLS_ENABLED = True
   TLS_CERTFILE = 'server.crt'
   TLS_KEYFILE = 'server.key'
   ```
3. Restart the server and client


## Configuration

All system settings can be customized in [common/config.py](common/config.py):

- **Network**: `SERVER_HOST`, `SERVER_PORT`
- **Protocol**: `BUFFER_SIZE`, `MAX_MESSAGE_SIZE`
- **Timeouts**: `COMMAND_TIMEOUT`, `CLIENT_TIMEOUT`
- **Multi-client**: `MAX_CLIENTS` (default: 50)
- **Logging**: `LOG_DIRECTORY`, `LOG_LEVEL`
- **Security**: `TLS_ENABLED`, `AUTH_ENABLED`, `AUTH_TOKEN`

## Project Structure

```
C2_server/
├── server/
│   ├── server.py           - Multi-threaded server implementation
│   ├── session.py          - ClientSession dataclass
│   └── session_manager.py  - Thread-safe session registry
├── client/
│   └── client.py           - Client agent with command execution
├── common/
│   ├── config.py           - Centralized configuration
│   ├── protocol.py         - Length-prefixed JSON protocol
│   └── logger.py           - Dual logging system
└── logs/                   - Log files (auto-created)
```

## License

This project is for educational purposes only. Use responsibly and only in authorized contexts.
