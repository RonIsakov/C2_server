"""
Configuration constants for C2 Server and Client.
This module centralizes all configurable values for the C2 system
"""


# Network Configuration
SERVER_HOST = '127.0.0.1'  # Server IP address (localhost for testing)
SERVER_PORT = 4444          # Server listening port (common C2 port)

# Protocol Configuration
BUFFER_SIZE = 4096          # Socket receive buffer size in bytes
LENGTH_PREFIX_SIZE = 4      # Size of length prefix in bytes (supports up to 4GB messages)
MAX_MESSAGE_SIZE = 100 * 1024 * 1024  # Maximum message size: 100 MB

# Command Execution Configuration
COMMAND_TIMEOUT = 30        # Maximum time for command execution in seconds

# Connection Configuration
CONNECTION_RETRY_DELAY = 2  # Initial delay between connection attempts in seconds
MAX_CONNECTION_RETRIES = 3  # Maximum number of connection retry attempts

# Multi-Client Configuration (Level 3)
MAX_CLIENTS = 50            # Maximum number of concurrent client connections
CLIENT_TIMEOUT = 300        # Client inactivity timeout in seconds (5 minutes)

# Logging Configuration
LOG_DIRECTORY = 'logs'                   # Directory for log files
LOG_FILE_PREFIX = 'c2_server'            # Prefix for log filenames
LOG_LEVEL = 'INFO'                       # Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_FORMAT = '%(asctime)s | %(levelname)-7s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'    # Timestamp format

# TLS Configuration (Level 4)
TLS_ENABLED = True
# Path to the server's certificate and key
TLS_CERTFILE = 'server.crt'
TLS_KEYFILE = 'server.key'
