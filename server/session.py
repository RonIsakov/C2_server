"""
Client Session Data Structure

This module defines the ClientSession dataclass that represents
a single connected client with all its associated state and resources.

Each session includes:
- Connection information (socket, address)
- Session identifiers (session_id, client_id)
- Communication channels (command queue)
- Thread management (handler thread reference)
- Logging (dedicated logger)
- Activity tracking (timestamps, connection status)

This is for authorized security testing and educational purposes only.
"""

import socket
import queue
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ClientSession:
    """
    Represents a single connected client session.

    This dataclass encapsulates all state and resources for one client,
    including the network connection, command queue, logging, and metadata.

    Attributes:
        session_id: Unique session identifier (SESSION-YYYYMMDDHHMMSS-xxxx)
        client_id: Client's hostname or unique identifier
        client_socket: TCP socket for this client
        client_address: Tuple of (ip_address, port)
        command_queue: Queue for operator commands to this client
        handler_thread: Thread handling this client's communication
        logger: Dedicated logger instance for this session
        registered_at: Timestamp when client registered
        last_activity: Timestamp of last command/response
        connected: Whether client is still connected
    """

    # Identifiers
    session_id: str
    client_id: str

    # Network
    client_socket: socket.socket
    client_address: tuple  # (ip, port)

    # Communication
    command_queue: queue.Queue = field(default_factory=queue.Queue)

    # Threading
    handler_thread: Optional[threading.Thread] = None

    # Logging
    logger: Optional[logging.Logger] = None

    # Timestamps
    registered_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # Status
    connected: bool = True

    def update_activity(self):
        """
        Update the last_activity timestamp to current time.
        """
        self.last_activity = datetime.now()

    def is_active(self) -> bool:
        """
        Check if the session is still active (connected).

        Returns:
            bool: True if client is connected, False otherwise
        """
        return self.connected

    def get_info_dict(self) -> dict:
        """
        Get a dictionary representation of session info (safe for display).

        Returns a snapshot of the session state suitable for displaying
        to the operator (e.g., in session listing).

        Returns:
            dict: Session information with string-formatted values
        """
        return {
            'client_id': self.client_id,
            'session_id': self.session_id,
            'address': f"{self.client_address[0]}:{self.client_address[1]}",
            'connected': self.connected,
            'registered_at': self.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
            'last_activity': self.last_activity.strftime('%Y-%m-%d %H:%M:%S')
        }
