from fastapi import FastAPI, Request
import asyncpg
import os
import json

app = FastAPI()

# Load DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# ------------------------------------------------------------------------
# DB CONNECT
# ------------------------------------------------------------------------
async def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL missing in environment variables")
    return await asyncpg.connect(DATABASE_URL)

# ------------------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/healthz_db")
async def healthz_db():
    try:
        if not DATABASE_URL:
            return {"ok": False, "err": "DATABASE_URL missing"}

        conn = await get_db_connection()
        await conn.execute("SELECT 1;")
        await conn.close()
        return {"ok": True}

    except Exception as e:
        return {"ok": False, "err": str(e)}

@app.post("/webhook/trade")
async def trade(req: Request):
    try:
        data = await req.json()
        deal_id   = data.get("deal_id")
        symbol    = data.get("symbol")
        volume    = data.get("volume")
        side      = data.get("side")
        entry     = data.get("entry_price")
        opened_at = data.get("opened_at_utc")
        status    = data.get("status")
        magic     = data.get("magic")

        conn = await get_db_connection()

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mt5_trades (
                id SERIAL PRIMARY KEY,
                deal_id BIGINT,
                symbol TEXT,
                volume FLOAT,
                side TEXT,
                entry_price FLOAT,
                opened_at_utc TEXT,
                status TEXT,
                magic BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        await conn.execute("""
            INSERT INTO mt5_trades(deal_id, symbol, volume, side, entry_price,
            opened_at_utc, status, magic)
            VALUES($1,$2,$3,$4,$5,$6,$7,$8)
        """,
        deal_id, symbol, volume, side, entry, opened_at, status, magic)

        await conn.close()

        return {"ok": True, "msg": "trade logged"}

    except Exception as e:
        return {"ok": False, "err": str(e)}
