# Makefile for C2 Server/Client System
# This provides convenient commands to run the server and client

# Python interpreter (use 'py' for Windows launcher, 'python3' for Linux/Mac)
PYTHON := py

# Project root directory
PROJECT_ROOT := $(shell cd)

# Set PYTHONPATH to include project root for imports
export PYTHONPATH := $(PROJECT_ROOT)

# Default target
.PHONY: help
help:
	@echo "C2 Server/Client - Available Commands"
	@echo "======================================"
	@echo "  make server      - Run the C2 server"
	@echo "  make client      - Run the C2 client"
	@echo "  make clean       - Remove Python cache files"
	@echo "  make help        - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  Host: 127.0.0.1"
	@echo "  Port: 4444"
	@echo "  Edit common/config.py to change settings"

# Run the server
.PHONY: server
server:
	@echo "[*] Starting C2 Server..."
	@echo "[*] PYTHONPATH=$(PYTHONPATH)"
	@echo ""
	$(PYTHON) server/server.py

# Run the client
.PHONY: client
client:
	@echo "[*] Starting C2 Client..."
	@echo "[*] PYTHONPATH=$(PYTHONPATH)"
	@echo ""
	$(PYTHON) client/client.py

# Clean Python cache files
.PHONY: clean
clean:
	@echo "[*] Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "[*] Clean complete"

# Show current configuration
.PHONY: config
config:
	@echo "Current Configuration:"
	@echo "====================="
	@$(PYTHON) -c "from common import config; print(f'Server Host: {config.SERVER_HOST}'); print(f'Server Port: {config.SERVER_PORT}'); print(f'Command Timeout: {config.COMMAND_TIMEOUT}s'); print(f'Max Message Size: {config.MAX_MESSAGE_SIZE / 1024 / 1024:.0f} MB')"
