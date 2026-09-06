"""
Configuration settings and constants for PolyArb.
"""
import os

# ─── Polymarket API Endpoints ─────────────────────────────────────
GAMMA_API_URL = os.environ.get("GAMMA_API_URL", "https://gamma-api.polymarket.com")
CLOB_API_URL = os.environ.get("CLOB_API_URL", "https://clob.polymarket.com")
CLOB_WS_URL = os.environ.get("CLOB_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market")

# ─── Blockchain / Web3 Settings ──────────────────────────────────
POLYGON_RPC_URL = os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com")
CTF_EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
CONDITIONAL_TOKENS_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC.e

# ─── Scanner & Execution Thresholds ──────────────────────────────
# Minimum gross profit percentage required to trigger an arbitrage alert
MIN_ARBITRAGE_SPREAD_PCT = float(os.environ.get("MIN_ARBITRAGE_SPREAD_PCT", "1.5"))

# Resolution lag criteria: token price must be between min and max probability
MIN_RESOLUTION_PROBABILITY = float(os.environ.get("MIN_RESOLUTION_PROBABILITY", "0.975"))
MAX_RESOLUTION_PROBABILITY = float(os.environ.get("MAX_RESOLUTION_PROBABILITY", "0.995"))

# Minimum 24h volume for market consideration ($)
MIN_VOLUME_USD = float(os.environ.get("MIN_VOLUME_USD", "5000.0"))

# Estimated slippage + taker fee buffer (%)
ESTIMATED_FEE_SLIPPAGE_PCT = float(os.environ.get("ESTIMATED_FEE_SLIPPAGE_PCT", "0.5"))

# ─── Paper Trading Defaults ──────────────────────────────────────
PAPER_STARTING_BALANCE_USDC = float(os.environ.get("PAPER_STARTING_BALANCE_USDC", "10000.0"))
MAX_POSITION_SIZE_USDC = float(os.environ.get("MAX_POSITION_SIZE_USDC", "500.0"))

# ─── Telegram Bot Settings ───────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ─── Search & AI Router Settings ─────────────────────────────────
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_ENGINE_ID = os.environ.get("GOOGLE_SEARCH_ENGINE_ID", "")
BRAVE_SEARCH_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Web Server Port
PORT = int(os.environ.get("PORT", "8080"))
