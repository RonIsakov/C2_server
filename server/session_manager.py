"""
Session Manager - Thread-Safe Multi-Client Session Management

This module provides the SessionManager class that manages multiple
concurrent client sessions in a thread-safe manner.

The SessionManager acts as a centralized registry for all active client
sessions, providing synchronized access to prevent race conditions when
multiple threads (listener, handlers, operator) need to access session data.

Key features:
- Thread-safe add/remove/get operations using locks
- Session listing with safe snapshots
- Client count tracking
- Disconnection marking
"""

import threading
from typing import Dict, List, Optional
from .session import ClientSession


class SessionManager:
    """
    Thread-safe manager for multiple client sessions.

    This class provides synchronized access to a dictionary of active
    client sessions, ensuring thread safety when multiple threads need
    to add, remove, or query sessions concurrently.

    The internal dictionary is protected by a threading.Lock, which is
    automatically acquired/released using context managers (with statement).

    Attributes:
        _sessions: Dictionary mapping client_id to ClientSession
        _lock: Threading lock for synchronizing access
    """

    def __init__(self):
        """
        Initialize an empty SessionManager.

        Creates an empty sessions dictionary and a lock for thread safety.
        """
        self._sessions: Dict[str, ClientSession] = {}
        self._lock = threading.Lock()

    def add_session(self, session: ClientSession) -> bool:
        """
        Add a new client session to the manager.

        Thread-safe operation that adds a session to the internal dictionary.
        Prevents duplicate client_ids by checking before adding.

        Args:
            session: ClientSession object to add

        Returns:
            bool: True if session was added successfully
                  False if client_id already exists
        """
        with self._lock:
            # Check if client_id already exists
            if session.client_id in self._sessions:
                return False

            # Add the session
            self._sessions[session.client_id] = session
            return True

    def remove_session(self, client_id: str) -> Optional[ClientSession]:
        """
        Remove and return a session by client_id.

        Thread-safe operation that removes a session from the dictionary
        and returns it. If the client_id doesn't exist, returns None.

        Args:
            client_id: The client identifier to remove

        Returns:
            ClientSession: The removed session if found
            None: If client_id doesn't exist
        """
        with self._lock:
            return self._sessions.pop(client_id, None)

    def get_session(self, client_id: str) -> Optional[ClientSession]:
        """
        Get a session by client_id (read-only access).

        Thread-safe operation that retrieves a session without removing it.
        Returns a reference to the actual session object (not a copy).

        Args:
            client_id: The client identifier to look up

        Returns:
            ClientSession: The session if found
            None: If client_id doesn't exist
        """
        with self._lock:
            return self._sessions.get(client_id)

    def list_sessions(self) -> List[dict]:
        """
        Get a snapshot of all active sessions as a list of dicts.

        Thread-safe operation that creates a copy of session information
        suitable for display. Returns dictionaries with formatted strings
        rather than raw session objects.

        Returns:
            List[dict]: List of session info dictionaries, each containing:
                - client_id: str
                - session_id: str
                - address: str (formatted as "ip:port")
                - connected: bool
                - registered_at: str (formatted timestamp)
                - last_activity: str (formatted timestamp)
        """
        with self._lock:
            # Create a snapshot of session info
            # Use get_info_dict() to get safe dictionary representation
            return [session.get_info_dict() for session in self._sessions.values()]

    def get_session_count(self) -> int:
        """
        Get the count of active sessions.

        Thread-safe operation that returns the number of sessions
        currently in the manager.

        Returns:
            int: Number of active sessions
        """
        with self._lock:
            return len(self._sessions)

    def mark_disconnected(self, client_id: str) -> bool:
        """
        Mark a session as disconnected without removing it.

        Thread-safe operation that sets the 'connected' flag to False.
        Useful for graceful cleanup where you want to mark a client as
        disconnected before removing the session.

        Args:
            client_id: The client identifier to mark as disconnected

        Returns:
            bool: True if session was found and marked
                  False if client_id doesn't exist
        """
        with self._lock:
            session = self._sessions.get(client_id)
            if session:
                session.connected = False
                return True
            return False

    def get_all_client_ids(self) -> List[str]:
        """
        Get a list of all client IDs currently in the manager.

        Thread-safe operation that returns a snapshot of all client_ids.
        Useful for iteration or batch operations.

        Returns:
            List[str]: List of client identifiers
        """
        with self._lock:
            return list(self._sessions.keys())
