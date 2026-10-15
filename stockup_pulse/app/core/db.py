"""
Re-export SQLModel database tables and queries for app.core.db namespace.
"""
from stockup_pulse.core.db import (
    LiveMarketPrice,
    User,
    init_db,
    seed_baseline_if_empty,
    upsert_scraped_product,
    query_live_market_substitute,
    authenticate_user,
    register_user,
    engine,
)

__all__ = [
    "LiveMarketPrice",
    "User",
    "init_db",
    "seed_baseline_if_empty",
    "upsert_scraped_product",
    "query_live_market_substitute",
    "authenticate_user",
    "register_user",
    "engine",
]
