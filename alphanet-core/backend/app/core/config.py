"""Central configuration loaded from the environment / `.env`.

Default network: **Base Sepolia** (`eip155:84532`) + test USDC + optional
`AWAL_X402_PAY_EXTRA` flags for `npx awal x402 pay`. For Base Mainnet,
override `NETWORK_CAIP_ID`, `USDC_CONTRACT_ADDRESS`, and clear
`AWAL_X402_PAY_EXTRA` as needed (see docs/PROJECT-NOTES.md).
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LIVE = x402/AWAL micropayments allowed for paid data; PAPER = free sources only.
    TRADING_MODE: str = "PAPER"  # PAPER | LIVE
    # DEMO_MODE replaces real market data with clearly-labeled synthetic headlines.
    DEMO_MODE: bool = False
    LOOP_INTERVAL_SECONDS: int = 30

    # Base Sepolia (testnet default — fund via Coinbase faucet, test USDC)
    NETWORK_CAIP_ID: str = "eip155:84532"
    USDC_CONTRACT_ADDRESS: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

    # Extra CLI tokens appended after `npx awal x402 pay ...` (chain / flags for your awal version)
    AWAL_X402_PAY_EXTRA: str = "--chain base-sepolia"

    # Guardrails (documented in docs/PROJECT-NOTES.md)
    MAX_DAILY_SPEND_USDC: float = 2.00
    MAX_PRICE_PER_SEARCH_USDC: float = 0.01
    EDGE_THRESHOLD: float = 0.05
    DAILY_DRAWDOWN_LIMIT_USDC: float = 5.00

    # x402 keyless gateways + optional REST (plan credits)
    TAVILY_402_ENDPOINT: str = "https://402.tavily.com/v1/search"
    TAVILY_REST_ENDPOINT: str = "https://api.tavily.com/search"
    TAVILY_API_KEY: str = ""
    # payTo address for our own 402 invoices. No default on purpose: selling
    # rationale over x402 is refused until the operator sets a real address.
    OUR_AWAL_WALLET_ADDRESS: str = ""

    # Inference (Groq = free-tier NLP extraction only; never portfolio math)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Monitoring — set SENTRY_DSN to capture FastAPI + awal subprocess failures
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    # Equity tickers the autonomous loop scouts each cycle
    WATCHLIST: str = "AAPL,MSFT,NVDA"

    @property
    def watchlist(self) -> List[str]:
        return [t.strip().upper() for t in self.WATCHLIST.split(",") if t.strip()]

    @property
    def is_live(self) -> bool:
        return self.TRADING_MODE.upper() == "LIVE"

    @property
    def tavily_key_ok(self) -> bool:
        key = (self.TAVILY_API_KEY or "").strip()
        return bool(key) and not key.lower().startswith("your_")

    @property
    def data_mode(self) -> str:
        """Primary scout data path shown in /health and the UI."""
        if self.DEMO_MODE:
            return "demo"
        if self.tavily_key_ok:
            return "yfinance+tavily_rest"
        if self.is_live:
            return "yfinance+tavily_x402"
        return "yfinance"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
