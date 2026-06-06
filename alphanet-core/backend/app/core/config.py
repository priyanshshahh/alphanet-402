"""Central configuration loaded from `.env` / `.env.example`.

Hackathon default: **Base Sepolia** (`eip155:84532`) + test USDC + optional
`AWAL_X402_PAY_EXTRA` flags for `npx awal x402 pay`. For Base Mainnet production,
override `NETWORK_CAIP_ID`, `USDC_CONTRACT_ADDRESS`, and clear `AWAL_X402_PAY_EXTRA`
as needed (see repo `CURSOR_DOCS.md`).
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load defaults from .env.example first, then let a real .env override them.
    model_config = SettingsConfigDict(
        env_file=(".env.example", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # LIVE = Tavily x402 + `npx awal x402 pay` when REST key is absent; PAPER = offline scout only.
    TRADING_MODE: str = "LIVE"  # PAPER | LIVE
    LOOP_INTERVAL_SECONDS: int = 30

    # Base Sepolia (hackathon default — fund via Coinbase faucet, test USDC)
    NETWORK_CAIP_ID: str = "eip155:84532"
    USDC_CONTRACT_ADDRESS: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

    # Extra CLI tokens appended after `npx awal x402 pay ...` (chain / flags for your awal version)
    AWAL_X402_PAY_EXTRA: str = "--chain base-sepolia"

    # Guardrails (CURSOR_DOCS.md §1)
    MAX_DAILY_SPEND_USDC: float = 2.00
    MAX_PRICE_PER_SEARCH_USDC: float = 0.01
    EDGE_THRESHOLD: float = 0.05
    DAILY_DRAWDOWN_LIMIT_USDC: float = 5.00

    # x402 keyless gateways + optional REST (plan credits)
    TAVILY_402_ENDPOINT: str = "https://402.tavily.com/v1/search"
    TAVILY_REST_ENDPOINT: str = "https://api.tavily.com/search"
    TAVILY_API_KEY: str = ""
    # Default matches project hackathon wallet; override in `.env` for other agents.
    OUR_AWAL_WALLET_ADDRESS: str = "0x4b97f492232c6C285F0F3b60c38fc4a7Ee13d675"

    # Inference (Groq = free-tier NLP extraction only; never portfolio math)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Monitoring — set SENTRY_DSN to capture FastAPI + awal subprocess failures
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"

    # Scouting
    WATCHLIST: str = "BTC,ETH,SOL"

    @property
    def watchlist(self) -> List[str]:
        return [t.strip().upper() for t in self.WATCHLIST.split(",") if t.strip()]

    @property
    def is_live(self) -> bool:
        return self.TRADING_MODE.upper() == "LIVE"

    @property
    def tavily_ingestion_mode(self) -> str:
        """Scout data path: Tavily REST, x402+AWAL, or offline fallback."""
        key = (self.TAVILY_API_KEY or "").strip()
        if key and not key.lower().startswith("your_"):
            return "tavily_rest_credits"
        if self.is_live:
            return "tavily_x402_awal"
        return "paper"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
