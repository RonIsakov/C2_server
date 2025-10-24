import json
import struct
import socket
from typing import Optional, Dict, Any
from . import config


def recv_exactly(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """
    Receive exactly num_bytes from a socket.

    This function handles the TCP streaming nature by looping until
    exactly the requested number of bytes have been received. This is
    critical because sock.recv(n) may return fewer than n bytes.

    Args:
        sock: The socket to receive from
        num_bytes: Exact number of bytes to receive

    Returns:
        bytes: Exactly num_bytes of data
        None: If connection closed or error occurred
    """
    data = b''  # Accumulator for received bytes

    while len(data) < num_bytes:
        # Calculate how many bytes we still need
        remaining = num_bytes - len(data)

        try:
            # Try to receive the remaining bytes
            chunk = sock.recv(remaining)

            if not chunk:
                return None

            # Append this chunk to our accumulated data
            data += chunk

        except socket.timeout:
            # Socket timeout - return None to signal error
            return None
        except (ConnectionResetError, BrokenPipeError, OSError):
            # Connection error - return None
            return None

    return data


def send_message(sock: socket.socket, message_dict: Dict[str, Any]) -> bool:
    """
    Protocol Steps:
        1. Serialize dict to JSON string
        2. Encode JSON string to UTF-8 bytes
        3. Calculate message length
        4. Pack length as 4-byte big-endian integer
        5. Send [length_prefix][json_bytes]

    Args:
        sock: The socket to send on
        message_dict: Python dictionary to send

    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        json_string = json.dumps(message_dict)
        json_bytes = json_string.encode('utf-8')
        message_length = len(json_bytes)

        # Pack length as 4-byte big-endian integer
        length_prefix = struct.pack('!I', message_length)

        #Combine length prefix and message, then send all at once
        full_message = length_prefix + json_bytes
        sock.sendall(full_message)

        return True

    except (BrokenPipeError, ConnectionResetError, OSError):
        # Connection error during send
        return False
    except (TypeError):
        # JSON serialization error
        return False
    except Exception:
        # Catch-all for unexpected errors
        return False


def receive_message(sock: socket.socket) -> Optional[Dict[str, Any]]:
    """
    Protocol Steps:
        1. Read exactly 4 bytes (length prefix)
        2. Unpack length from big-endian integer
        3. Read exactly that many bytes (JSON payload)
        4. Decode UTF-8 bytes to string
        5. Parse JSON string to dictionary

    Args:
        sock: The socket to receive from

    Returns:
        dict: Parsed message as a dictionary
        None: If connection closed or error occurred
    """
    try:
        # Read exactly LENGTH_PREFIX_SIZE bytes for the length prefix
        length_bytes = recv_exactly(sock, config.LENGTH_PREFIX_SIZE)
        if length_bytes is None:
            # Connection closed or error
            return None

        message_length = struct.unpack('!I', length_bytes)[0]

        # Validate message size doesn't exceed maximum
        if message_length > config.MAX_MESSAGE_SIZE:
            return None

        # Read exactly message_length bytes (the JSON payload)
        json_bytes = recv_exactly(sock, message_length)
        if json_bytes is None:
            # Connection closed mid-message
            return None

        # Decode UTF-8 bytes to string
        json_string = json_bytes.decode('utf-8')

        # Parse JSON string to dictionary
        message_dict = json.loads(json_string)

        return message_dict

    except (UnicodeDecodeError, json.JSONDecodeError):
        # Malformed message - invalid UTF-8 or invalid JSON
        return None
    except (struct.error, ValueError):
        # Invalid length prefix
        return None
    except Exception:
        # Catch-all for unexpected errors
        return None
