"""x402 payment middleware for paywalled API routes.

Uses the free x402.org facilitator on Base Sepolia (eip155:84532).
Only activates when X402_PAY_TO is set in the environment.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from .config import settings

log = logging.getLogger("x402")


def setup_x402(app: FastAPI) -> None:
    if not settings.x402_pay_to:
        log.info("x402 paywall disabled (set X402_PAY_TO to enable)")
        return

    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer

    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=settings.x402_facilitator_url)
    )
    server = x402ResourceServer(facilitator)
    server.register(settings.x402_network, ExactEvmServerScheme())

    routes = {
        "GET /api/trade/:trade_id/rationale": RouteConfig(
            accepts=[
                PaymentOption(
                    scheme="exact",
                    pay_to=settings.x402_pay_to,
                    price=settings.x402_price,
                    network=settings.x402_network,
                ),
            ],
            mime_type="application/json",
            description=(
                "Trade rationale: news article, LLM signal, and market snapshot "
                "that produced this trade."
            ),
        ),
    }

    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
    log.info(
        "x402 paywall enabled: GET /api/trade/:trade_id/rationale -> %s @ %s (%s)",
        settings.x402_pay_to,
        settings.x402_price,
        settings.x402_network,
    )
