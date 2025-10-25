"""
C2 Server Implementation

Level 1 & 2: Basic single-client server with logging
Level 3: Multi-client support with concurrent connections

This module implements the command and control server that:
- Accepts incoming client connections
- Receives client registration
- Provides an operator interface for sending commands
- Displays command results from clients
- Supports multiple concurrent clients (Level 3)

This is for authorized security testing and educational purposes only.
"""

import socket
import sys
import uuid
import logging
import threading
import queue
import time
from datetime import datetime
from typing import Optional, Dict
from common import config, protocol, logger
from server.session import ClientSession
from server.session_manager import SessionManager
import ssl


def generate_session_id() -> str:
    """
    Generate a unique session ID for tracking client sessions.

    Format: SESSION-{timestamp}-{random_suffix}
    Example: SESSION-20251024140933-a7f3

    Returns:
        str: Unique session identifier
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_suffix = uuid.uuid4().hex[:4]
    return f"SESSION-{timestamp}-{random_suffix}"


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


def connection_listener(
    server_socket: socket.socket,
    session_manager: SessionManager,
    main_logger: logging.Logger,
    shutdown_event: threading.Event,
    ssl_context: Optional[ssl.SSLContext]
    
):
    """
    Accept incoming client connections and spawn handler threads.

    This function runs in a dedicated listener thread and continuously
    accepts new client connections. For each connection, it spawns a
    new client_handler thread to manage that client.

    The listener respects the MAX_CLIENTS configuration limit and will
    reject connections if the limit is reached.

    Args:
        server_socket: The listening server socket
        session_manager: Shared SessionManager for all sessions
        main_logger: Logger for server-level events
        shutdown_event: Event to signal shutdown

    Returns:
        None (runs until shutdown_event is set)
    """
    main_logger.info("[MAIN] Connection listener thread started")
    print("[*] Connection listener started")
    print("[*] Waiting for client connections...")
    print()

    # Set socket timeout for responsive shutdown checking
    server_socket.settimeout(1.0)

    while not shutdown_event.is_set():
        try:
            # Check if we've reached max clients
            current_clients = session_manager.get_session_count()
            if current_clients >= config.MAX_CLIENTS:
                # At capacity: avoid busy-spin by sleeping briefly
                time.sleep(0.1)
                continue

            # Try to accept a connection (will timeout after 1 second)
            try:
                client_socket, client_address = server_socket.accept()
            except socket.timeout:
                # No connection received, loop again
                continue
                        # Accept new connection
            if ssl_context:
                try:
                    # Wrap the raw socket in an SSL socket
                    client_socket = ssl_context.wrap_socket(client_socket, server_side=True)
                    main_logger.info(f"[MAIN] TLS handshake successful for {client_address[0]}:{client_address[1]}")
                except ssl.SSLError as e:
                    main_logger.error(f"[MAIN] TLS handshake failed for {client_address[0]}:{client_address[1]}: {e}")
                    client_socket.close()
                    continue

            # Log the new connection
            main_logger.info(f"[MAIN] New connection from {client_address[0]}:{client_address[1]}")
            print(f"[+] Client connected from {client_address[0]}:{client_address[1]}")

            # Spawn a new thread to handle this client
            handler_thread = threading.Thread(
                target=client_handler,
                args=(client_socket, client_address, session_manager, main_logger),
                daemon=True,
                name=f"ClientHandler-{client_address[0]}:{client_address[1]}"
            )
            handler_thread.start()

            main_logger.info(f"[MAIN] Handler thread started for {client_address[0]}:{client_address[1]}")

        except Exception as e:
            if not shutdown_event.is_set():
                main_logger.error(f"[MAIN] Error in listener loop: {e}")
                print(f"[!] ERROR in listener: {e}")

    main_logger.info("[MAIN] Connection listener thread shutting down")
    print("[*] Connection listener stopped")


def start_server(main_logger: logging.Logger) -> Optional[socket.socket]:
    """
    Initialize and start the TCP server (Level 3: Multi-client version).

    Creates a TCP socket, binds to the configured host and port,
    and starts listening for connections. Does NOT accept connections -
    the connection_listener thread handles that.

    Args:
        main_logger: Logger for server-level events

    Returns:
        socket.socket: Server socket if successful
        None: If server startup fails
    """
    try:
        # Create TCP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set socket options to reuse address (helpful for quick restarts)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to configured address and port
        server_socket.bind((config.SERVER_HOST, config.SERVER_PORT))

        # Listen for incoming connections (queue up to MAX_CLIENTS)
        server_socket.listen(config.MAX_CLIENTS)

        print(f"[*] Server listening on {config.SERVER_HOST}:{config.SERVER_PORT}")
        print(f"[*] Max clients: {config.MAX_CLIENTS}")
        print()

        main_logger.info(f"[MAIN] Server started on {config.SERVER_HOST}:{config.SERVER_PORT}")
        main_logger.info(f"[MAIN] Max clients: {config.MAX_CLIENTS}")

        return server_socket

    except PermissionError:
        print(f"[!] ERROR: Permission denied. Cannot bind to port {config.SERVER_PORT}")
        print("[!] Try using a port > 1024 or run with elevated privileges")
        main_logger.error(f"[MAIN] Permission denied on port {config.SERVER_PORT}")
        return None
    except OSError as e:
        print(f"[!] ERROR: Failed to start server: {e}")
        main_logger.error(f"[MAIN] Failed to start server: {e}")
        return None
    except Exception as e:
        print(f"[!] ERROR: Unexpected error during server startup: {e}")
        main_logger.error(f"[MAIN] Unexpected error during startup: {e}")
        return None


def handle_registration(client_socket: socket.socket, session_id: str, log: logging.Logger) -> Optional[str]:
    """
    Handle client registration protocol.

    Receives and validates the registration message from the client,
    which should contain the client's ID/hostname and timestamp.

    Args:
        client_socket: The connected client socket
        session_id: The session identifier for logging
        log: Logger instance for this session

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
            log.error(f"[{session_id}] Failed to receive registration message")
            return None

        # LOG: Registration message received
        log.info(f"[{session_id}] Registration message received: {reg_message}")

        # Validate message type
        if reg_message.get('type') != 'registration':
            print(f"[!] ERROR: Invalid message type: {reg_message.get('type')}")
            log.error(f"[{session_id}] Invalid registration message type: {reg_message.get('type')}")
            return None

        # Extract client information
        client_id = reg_message.get('client_id')
        timestamp = reg_message.get('timestamp')

        if not client_id:
            print("[!] ERROR: Registration missing client_id")
            log.error(f"[{session_id}] Registration missing client_id")
            return None

        # Display registration info
        print(f"[+] Client registered successfully!")
        print(f"    Client ID: {client_id}")
        print(f"    Timestamp: {timestamp}")
        print()

        # LOG: Successful registration
        log.info(f"[{session_id}] Client registered successfully: {client_id}")

        return client_id

    except Exception as e:
        print(f"[!] ERROR: Registration failed: {e}")
        log.error(f"[{session_id}] Registration failed: {e}")
        return None


def client_handler(
    client_socket: socket.socket,
    client_address: tuple,
    session_manager: SessionManager,
    main_logger: logging.Logger
):
    """
    Handle a single client connection in a dedicated thread.

    This function manages the complete lifecycle of a client connection:
    1. Generate session ID and create logger
    2. Handle client registration
    3. Create and register ClientSession
    4. Process commands from queue
    5. Send results back
    6. Cleanup on disconnect

    This function runs in its own thread for each connected client,
    enabling concurrent multi-client support.

    Args:
        client_socket: The connected client's socket
        client_address: Tuple of (ip_address, port)
        session_manager: Shared SessionManager for registering this session
        main_logger: Main logger for server-level events

    Returns:
        None (thread exits when client disconnects)
    """
    session = None
    session_id = generate_session_id()
    log = logger.setup_logger(session_id)

    try:
        # Log the new connection
        log.info(f"[{session_id}] Client handler started for {client_address[0]}:{client_address[1]}")

        # Handle client registration
        client_id = handle_registration(client_socket, session_id, log)

        if client_id is None:
            log.error(f"[{session_id}] Registration failed, closing connection")
            return

        # Continue using the same per-session logger (session_id-named file)
        # to keep all session events in a single log file.

        # Create ClientSession object
        session = ClientSession(
            session_id=session_id,
            client_id=client_id,
            client_socket=client_socket,
            client_address=client_address,
            command_queue=queue.Queue(),
            handler_thread=threading.current_thread(),
            logger=log,
            registered_at=datetime.now(),
            last_activity=datetime.now(),
            connected=True
        )

        # Add session to manager
        if not session_manager.add_session(session):
            log.error(f"[{session_id}] Client ID {client_id} already exists!")
            print(f"[!] ERROR: Client ID {client_id} is already connected")
            return

        log.info(f"[{session_id}] Session registered in manager: {client_id}")
        print(f"[+] Client {client_id} ready for commands")
        print()

        # Main command loop - wait for commands from operator
        while session.connected:
            try:
                # Wait for command from operator (with timeout for responsive shutdown)
                command = session.command_queue.get(timeout=1.0)

                # Prepare command message
                command_message = {
                    'type': 'command',
                    'command': command
                }

                # LOG: Command sent
                log.info(f"[{session_id}] Command sent to {client_id}: {command}")

                # Send command to client
                success = protocol.send_message(client_socket, command_message)

                if not success:
                    log.error(f"[{session_id}] Failed to send command to {client_id}")
                    print(f"[!] ERROR: Failed to send command to {client_id}")
                    break

                # Receive result from client
                result_message = protocol.receive_message(client_socket)

                if result_message is None:
                    log.error(f"[{session_id}] Failed to receive result from {client_id}")
                    print(f"[!] ERROR: Failed to receive result from {client_id}")
                    break

                # Validate result message type
                if result_message.get('type') != 'result':
                    log.warning(f"[{session_id}] Unexpected message type from {client_id}: {result_message.get('type')}")
                    continue

                # LOG: Response received
                return_code = result_message.get('return_code', -1)
                log.info(f"[{session_id}] Response received from {client_id} (return_code={return_code})")

                # Update activity timestamp
                session.update_activity()

                # Display results with client context
                print(f"\n[Result from {client_id}]")
                display_results(result_message)

            except queue.Empty:
                # No command in queue, continue waiting
                continue

            except Exception as e:
                log.error(f"[{session_id}] Error in command loop: {e}")
                print(f"[!] ERROR: Exception in handler for {client_id}: {e}")
                break

    except Exception as e:
        log.error(f"[{session_id}] Unexpected error in client handler: {e}")
        print(f"[!] ERROR: Unexpected error handling client: {e}")

    finally:
        # Cleanup: always execute, even on exception
        if session:
            # Mark as disconnected
            session.connected = False

            # Remove from session manager
            removed = session_manager.remove_session(session.client_id)
            if removed:
                log.info(f"[{session_id}] Session removed from manager: {session.client_id}")
                print(f"[-] Client {session.client_id} disconnected")
                print()

        # Close socket
        try:
            client_socket.close()
            log.info(f"[{session_id}] Client socket closed")
        except:
            pass

        log.info(f"[{session_id}] Client handler thread exiting")


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
    Display available operator commands (Level 3: Multi-client version).
    """
    print()
    print("Available Commands:")
    print("  sessions           - List all active client sessions")
    print("  use <client_id>    - Switch to a specific client session")
    print("  help               - Show this help message")
    print("  exit, quit         - Close all connections and exit server")
    print()
    print("When a client is selected (using 'use <client_id>'):")
    print("  Any other input will be sent as a shell command to that client")
    print()


def operator_interface(
    session_manager: SessionManager,
    main_logger: logging.Logger,
    shutdown_event: threading.Event
):
    """
    Main operator interface loop (Level 3: Multi-client version).

    Provides an interactive command-line interface for the operator to:
    - List active client sessions
    - Switch between client sessions
    - Send commands to the active client
    - Exit gracefully

    This function runs in the main thread and interacts with client
    handler threads via the SessionManager and command queues.

    Args:
        session_manager: Shared SessionManager for all sessions
        main_logger: Logger for operator actions
        shutdown_event: Event to signal shutdown to all threads

    Returns:
        None (runs until operator exits)
    """
    print("=" * 60)
    print("OPERATOR INTERFACE - Multi-Client Mode")
    print("=" * 60)
    print("Type 'help' for available commands")
    print("Type 'sessions' to list connected clients")
    print()

    current_client_id = None  # Track which client is currently active

    try:
        while not shutdown_event.is_set():
            # Build prompt based on whether a client is selected
            if current_client_id:
                prompt = f"C2 [{current_client_id}]> "
            else:
                prompt = "C2> "

            # Get command from operator
            try:
                command = input(prompt).strip()
            except EOFError:
                # Handle Ctrl+D
                print()
                print("[*] EOF received. Exiting...")
                main_logger.info("[MAIN] EOF received, exiting operator interface")
                break

            # Handle empty input
            if not command:
                continue

            # Handle special commands
            if command.lower() in ['exit', 'quit']:
                print("[*] Shutting down server...")
                main_logger.info("[MAIN] Operator requested exit")
                shutdown_event.set()
                break

            elif command.lower() == 'help':
                display_help()
                continue

            elif command.lower() == 'sessions':
                # List all active sessions
                sessions = session_manager.list_sessions()
                print()
                print(f"Active Sessions ({len(sessions)}):")
                print("-" * 80)

                if not sessions:
                    print("  (no active sessions)")
                else:
                    for s in sessions:
                        status = "CONNECTED" if s['connected'] else "DISCONNECTED"
                        active_marker = " <-- ACTIVE" if s['client_id'] == current_client_id else ""
                        print(f"  [{status}] {s['client_id']:<20} {s['address']:<21} ({s['session_id']}){active_marker}")

                print("-" * 80)
                print()
                main_logger.info(f"[MAIN] Operator listed sessions (count: {len(sessions)})")
                continue

            elif command.lower().startswith('use '):
                # Switch to a specific client
                target_client_id = command[4:].strip()

                if not target_client_id:
                    print("[!] ERROR: Please specify a client_id (e.g., 'use LAPTOP-ABC')")
                    continue

                # Verify the session exists
                session = session_manager.get_session(target_client_id)

                if session is None:
                    print(f"[!] ERROR: No session found for client '{target_client_id}'")
                    print("[*] Use 'sessions' command to see available clients")
                    continue

                if not session.connected:
                    print(f"[!] WARNING: Client '{target_client_id}' is disconnected")
                    print("[*] You can select it, but commands will fail")

                # Switch to this client
                current_client_id = target_client_id
                print(f"[*] Switched to session: {current_client_id}")
                main_logger.info(f"[MAIN] Operator switched to session: {current_client_id}")
                continue

            else:
                # Regular command - send to active client
                if not current_client_id:
                    print("[!] ERROR: No active session selected")
                    print("[*] Use 'sessions' to list clients, then 'use <client_id>' to select one")
                    continue

                # Get the session
                session = session_manager.get_session(current_client_id)

                if session is None:
                    print(f"[!] ERROR: Session '{current_client_id}' no longer exists")
                    print("[*] Client may have disconnected. Use 'sessions' to see active clients")
                    current_client_id = None
                    continue

                if not session.connected:
                    print(f"[!] ERROR: Client '{current_client_id}' is disconnected")
                    current_client_id = None
                    continue

                # Queue the command for the client handler thread
                session.command_queue.put(command)
                main_logger.info(f"[MAIN] Command queued for {current_client_id}: {command}")

                # Note: Results will be displayed by the client_handler thread
                # No need to wait here - the handler thread prints results directly

    except KeyboardInterrupt:
        # Handle Ctrl+C
        print()
        print("[*] Keyboard interrupt received. Shutting down...")
        main_logger.info("[MAIN] Keyboard interrupt received")
        shutdown_event.set()

    except Exception as e:
        print(f"[!] ERROR: Unexpected error in operator interface: {e}")
        main_logger.error(f"[MAIN] Unexpected error in operator interface: {e}")
        shutdown_event.set()


def main():
    """
    Main entry point for the C2 server (Level 3: Multi-client version).

    Orchestrates the multi-client server startup:
    1. Display banner
    2. Create main logger
    3. Start server socket
    4. Create session manager
    5. Start listener thread
    6. Run operator interface (main thread)
    7. Graceful shutdown of all threads and connections
    """
    # Display banner
    display_banner()

    # Create main logger for server-level events
    main_logger = logger.setup_logger("MAIN")
    main_logger.info("[MAIN] C2 Server starting...")

    # Start server (create and bind socket)
    server_socket = start_server(main_logger)
    if server_socket is None:
        print("[!] Server startup failed. Exiting.")
        main_logger.error("[MAIN] Server startup failed")
        sys.exit(1)

    ssl_context = None
    if config.TLS_ENABLED:
        try:
            print("[*] TLS enabled. Loading certificate...")
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=config.TLS_CERTFILE, keyfile=config.TLS_KEYFILE)
            print("[+] Certificate loaded successfully")
        except Exception as e:
            print(f"[!] ERROR: Failed to load TLS certificate: {e}")
            main_logger.error(f"[MAIN] Failed to load TLS: {e}")
            server_socket.close()
            sys.exit(1)

    # Create session manager
    session_manager = SessionManager()
    main_logger.info("[MAIN] Session manager initialized")

    # Create shutdown event for coordinating thread shutdown
    shutdown_event = threading.Event()

    # Start connection listener thread
    listener_thread = threading.Thread(
        target=connection_listener,
        args=(server_socket, session_manager, main_logger, shutdown_event, ssl_context), 
        daemon=True,
        name="ConnectionListener"
    )
    listener_thread.start()
    main_logger.info("[MAIN] Listener thread started")

    try:
        # Run operator interface in main thread (blocks here)
        operator_interface(session_manager, main_logger, shutdown_event)

    finally:
        # Cleanup: shutdown all threads and close all connections
        print()
        print("[*] Shutting down server...")
        main_logger.info("[MAIN] Beginning shutdown sequence")

        # Signal shutdown to all threads
        shutdown_event.set()

        # Wait for listener thread to finish (with timeout)
        print("[*] Stopping connection listener...")
        listener_thread.join(timeout=5.0)
        if listener_thread.is_alive():
            main_logger.warning("[MAIN] Listener thread did not stop gracefully")
        else:
            main_logger.info("[MAIN] Listener thread stopped")

        # Close all client connections
        print("[*] Closing all client connections...")
        client_ids = session_manager.get_all_client_ids()

        for client_id in client_ids:
            session = session_manager.get_session(client_id)
            if session:
                try:
                    # Mark as disconnected
                    session.connected = False

                    # Close socket
                    session.client_socket.close()
                    main_logger.info(f"[MAIN] Closed connection to {client_id}")
                except Exception as e:
                    main_logger.error(f"[MAIN] Error closing connection to {client_id}: {e}")

        # Give handler threads time to exit gracefully
        print("[*] Waiting for handler threads to finish...")
        import time
        time.sleep(2)

        # Close server socket
        try:
            server_socket.close()
            print("[*] Server socket closed")
            main_logger.info("[MAIN] Server socket closed")
        except Exception as e:
            main_logger.error(f"[MAIN] Error closing server socket: {e}")

        print("[*] Server shutdown complete")
        main_logger.info("[MAIN] Server shutdown complete")
        print()


if __name__ == '__main__':
    main()
