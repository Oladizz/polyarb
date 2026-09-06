"""
WebSocket listener for Polymarket CLOB real-time price & order book feeds.
"""
import asyncio
import json
from collections.abc import Callable

import websockets

from app.core.config import CLOB_WS_URL


class ClobWebSocketFeed:
    """Subscribes to live order book updates from Polymarket's CLOB WebSocket."""

    def __init__(self, ws_url: str = CLOB_WS_URL):
        self.ws_url = ws_url
        self.subscribed_tokens: list[str] = []
        self.callbacks: list[Callable[[dict], None]] = []
        self._running = False

    def add_callback(self, callback: Callable[[dict], None]):
        """Registers a callback function for incoming market events."""
        self.callbacks.append(callback)

    async def connect_and_listen(self, token_ids: list[str]):
        """Connects to the WebSocket and listens for messages."""
        self.subscribed_tokens = token_ids
        self._running = True

        while self._running:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=20) as ws:
                    for tid in token_ids:
                        subscribe_msg = {
                            "type": "subscribe",
                            "channel": "market",
                            "token_id": tid
                        }
                        await ws.send(json.dumps(subscribe_msg))

                    while self._running:
                        msg_str = await ws.recv()
                        data = json.loads(msg_str)
                        for cb in self.callbacks:
                            try:
                                cb(data)
                            except Exception as e:
                                print(f"Error in WS callback: {e}")

            except asyncio.CancelledError:
                self._running = False
                break
            except Exception as e:
                print(f"WebSocket connection error: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

    def stop(self):
        """Stops the WebSocket listener."""
        self._running = False
