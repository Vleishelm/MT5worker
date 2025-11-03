from fastapi import FastAPI, Request
import os, asyncpg, json

app = FastAPI()

DB_URL = os.getenv("DATABASE_URL")

# ===== DB CONNECTIE ==========
async def get_conn():
    return await asyncpg.connect(DB_URL)

# ===== HEALTHCHECKS ==========
@app.get("/healthz")
async def health_basic():
    return {"ok": True}

@app.get("/healthz_db")
async def health_db():
    try:
        conn = await get_conn()
        await conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)}

# ===== TRADE WEBHOOK =========
@app.post("/webhook/trade")
async def webhook_trade(req: Request):
    try:
        body = await req.json()
        conn = await get_conn()
        await conn.execute("""
            INSERT INTO trades (magic, symbol, order_type, volume, price, opened_at_utc, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        body.get("magic"),
        body.get("symbol"),
        body.get("order_type"),
        body.get("volume"),
        body.get("price"),
        body.get("opened_at_utc"),
        body.get("status")
        )
        await conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)}
