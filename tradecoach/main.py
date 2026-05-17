"""
FastAPI application entrypoint.
"""

import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tradecoach.api import accounts, analysis, coaching, dashboard, trades, upload, users

logger = logging.getLogger(__name__)

NEWS_COLLECT_INTERVAL = 30 * 60  # 30 minutes


async def _news_collector_loop() -> None:
    """Run news collection on startup, then every 30 minutes."""
    from tradecoach.services.news_collector import collect_and_store_news

    while True:
        try:
            count = await asyncio.to_thread(collect_and_store_news)
            logger.info("News collector: %d new items", count)
        except Exception:
            logger.exception("News collector failed")
        await asyncio.sleep(NEWS_COLLECT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — launches background news collector."""
    task = asyncio.create_task(_news_collector_loop())
    logger.info("News collector background task started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="TradeCoach API",
    version="0.1.0",
    description="AI trading coach for retail FX traders",
    lifespan=lifespan,
)

# CORS — allow all origins in dev, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://tradeguard-cyan.vercel.app",
        "https://trading-coach.app",
        "https://www.trading-coach.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(coaching.router, prefix="/api/coaching", tags=["coaching"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(users.router, prefix="/api/users", tags=["users"])


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
