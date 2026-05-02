"""FastAPI 入口."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import backtest, portfolio, stock, watchlist

load_dotenv()

app = FastAPI(title="Financial Dashboard API", version="0.1.0")

frontend = os.getenv("FRONTEND_URL", "")
allow_origins = [
    origin
    for origin in [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        frontend,
    ]
    if origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stock.router, prefix="/api")
app.include_router(watchlist.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "financial-dashboard-api"}


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
