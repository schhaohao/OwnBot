from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from ownbot.bus.events import OutboundMessage
from ownbot.bus.queue import MessageBus
from ownbot.channels.base import BaseChannel
from ownbot.config.schema import WhatsAppConfig


class WhatsAppChannel(BaseChannel):
    """
    WhatsApp channel that connects to a Node.js bridge.

    The bridge uses @whiskeysockets/baileys to handle the WhatsApp Web protocol.
    Communication between Python and Node.js is via WebSocket.
    """

    name = "whatsapp"
    display_name = "WhatsApp"

    def __init__(self, config: WhatsAppConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: WhatsAppConfig = config
        self._ws = None
        self._connected = False
        self._bridge_process: Optional[subprocess.Popen] = None
        self._processed_message_ids: OrderedDict[str, None] = OrderedDict()
        self._bridge_dir = Path(__file__).parent.parent.parent / "whatsapp-bridge"
        self._auth_dir = Path.home() / ".ownbot" / "workspace" / "whatsapp-auth"

    def _ensure_bridge_installed(self) -> bool:
        """Ensure the bridge is installed."""
        bridge_package_json = self._bridge_dir / "package.json"
        node_modules = self._bridge_dir / "node_modules"
        
        if not bridge_package_json.exists():
            logger.error("WhatsApp bridge not found at {}", self._bridge_dir)
            return False
        
        if not node_modules.exists():
            logger.info("Installing WhatsApp bridge dependencies...")
            try:
                subprocess.run(
                    ["npm", "install"],
                    cwd=self._bridge_dir,
                    check=True,
                    capture_output=True,
                    text=True
                )
                logger.info("WhatsApp bridge dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error("Failed to install bridge dependencies: {}", e.stderr)
                return False
            except FileNotFoundError:
                logger.error("npm not found. Please install Node.js and npm first.")
                return False
        
        return True

    def _start_bridge_server(self) -> bool:
        """Start the bridge server."""
        if not self._ensure_bridge_installed():
            return False
        
        # Ensure auth directory exists
        self._auth_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if bridge is already running
        if self._is_bridge_running():
            logger.info("WhatsApp bridge is already running")
            return True
        
        logger.info("Starting WhatsApp bridge server...")
        
        try:
            env = os.environ.copy()
            env["PORT"] = "3001"
            env["AUTH_DIR"] = str(self._auth_dir)
            
            # Start the bridge server - output directly to terminal so user can see QR code
            self._bridge_process = subprocess.Popen(
                ["node", "server.js"],
                cwd=self._bridge_dir,
                env=env,
                stdout=None,  # Use parent's stdout
                stderr=None,  # Use parent's stderr
                text=True
            )
            
            # Wait a bit for the server to start
            time.sleep(3)
            
            # Check if process is still running
            if self._bridge_process.poll() is not None:
                logger.error("Bridge server failed to start")
                return False
            
            logger.info("WhatsApp bridge server started on pid {}", self._bridge_process.pid)
            return True
            
        except Exception as e:
            logger.error("Failed to start bridge server: {}", e)
            return False

    def _is_bridge_running(self) -> bool:
        """Check if bridge server is already running."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 3001))
            sock.close()
            return result == 0
        except:
            return False

    def _stop_bridge_server(self) -> None:
        """Stop the bridge server."""
        if self._bridge_process:
            logger.info("Stopping WhatsApp bridge server...")
            self._bridge_process.terminate()
            try:
                self._bridge_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._bridge_process.kill()
            self._bridge_process = None

    async def start(self) -> None:
        """Start the WhatsApp channel by connecting to the bridge."""
        import websockets

        # Start bridge server if not running
        if not self._start_bridge_server():
            logger.error("Failed to start WhatsApp bridge. WhatsApp channel will be disabled.")
            return

        bridge_url = self.config.bridge_url

        logger.info("Connecting to WhatsApp bridge at {}...", bridge_url)

        self._running = True

        while self._running:
            try:
                async with websockets.connect(bridge_url) as ws:
                    self._ws = ws
                    # Send auth token if configured
                    if self.config.bridge_token:
                        await ws.send(json.dumps({"type": "auth", "token": self.config.bridge_token}))
                    self._connected = True
                    logger.info("Connected to WhatsApp bridge")

                    # Listen for messages
                    async for message in ws:
                        try:
                            await self._handle_bridge_message(message)
                        except Exception as e:
                            logger.error("Error handling bridge message: {}", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                self._ws = None
                logger.warning("WhatsApp bridge connection error: {}", e)

                if self._running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the WhatsApp channel."""
        self._running = False
        self._connected = False

        if self._ws:
            await self._ws.close()
            self._ws = None
        
        self._stop_bridge_server()

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through WhatsApp."""
        if not self._ws or not self._connected:
            logger.warning("WhatsApp bridge not connected")
            return

        try:
            payload = {
                "type": "send",
                "to": msg.chat_id,
                "text": msg.content
            }
            await self._ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            logger.error("Error sending WhatsApp message: {}", e)

    async def _handle_bridge_message(self, raw: str) -> None:
        """Handle a message from the bridge."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON from bridge: {}", raw[:100])
            return

        msg_type = data.get("type")

        if msg_type == "message":
            # Incoming message from WhatsApp
            # Deprecated by whatsapp: old phone number style typically: <phone>@s.whatspp.net
            pn = data.get("pn", "")
            # New LID sytle typically:
            sender = data.get("sender", "")
            content = data.get("content", "")
            message_id = data.get("id", "")

            if message_id:
                if message_id in self._processed_message_ids:
                    return
                self._processed_message_ids[message_id] = None
                while len(self._processed_message_ids) > 1000:
                    self._processed_message_ids.popitem(last=False)

            # Extract just the phone number or lid as chat_id
            user_id = pn if pn else sender
            sender_id = user_id.split("@")[0] if "@" in user_id else user_id
            logger.info("Sender {}", sender)

            # Handle voice transcription if it's a voice message
            if content == "[Voice Message]":
                logger.info("Voice message received from {}, but direct download from bridge is not yet supported.", sender_id)
                content = "[Voice Message: Transcription not available for WhatsApp yet]"

            # Extract media paths (images/documents/videos downloaded by the bridge)
            media_paths = data.get("media") or []

            # Build content tags matching Telegram's pattern: [image: /path] or [file: /path]
            if media_paths:
                for p in media_paths:
                    mime, _ = mimetypes.guess_type(p)
                    media_type = "image" if mime and mime.startswith("image/") else "file"
                    media_tag = f"[{media_type}: {p}]"
                    content = f"{content}\n{media_tag}" if content else media_tag

            await self._handle_message(
                sender_id=sender_id,
                chat_id=sender,  # Use full LID for replies
                content=content,
                media=media_paths,
                metadata={
                    "message_id": message_id,
                    "timestamp": data.get("timestamp"),
                    "is_group": data.get("isGroup", False)
                }
            )

        elif msg_type == "status":
            # Connection status update
            status = data.get("status")
            logger.info("WhatsApp status: {}", status)

            if status == "connected":
                self._connected = True
            elif status == "disconnected":
                self._connected = False

        elif msg_type == "qr":
            # QR code for authentication
            logger.info("Scan QR code in the bridge terminal to connect WhatsApp")

        elif msg_type == "error":
            logger.error("WhatsApp bridge error: {}", data.get('error'))
