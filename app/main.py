# app/main.py
import os
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ["DATABASE_URL"]
INGEST_SECRET = os.environ.get("INGEST_SECRET", "")

app = FastAPI()

def conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

class TradeIn(BaseModel):
    ticket: int
    symbol: str
    direction: str  # 'buy' of 'sell'
    lot: float
    entry_price: float
    opened_at_utc: float | str   # epoch of ISO
    status: str = "open"
    magic: int | None = None

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest/trade")
def ingest_trade(body: TradeIn, x_mt5_sig: str | None = Header(None)):
    if INGEST_SECRET and x_mt5_sig != INGEST_SECRET:
        raise HTTPException(401, "bad signature")

    # tijd normaliseren
    if isinstance(body.opened_at_utc, (int, float)):
        opened = datetime.fromtimestamp(body.opened_at_utc, tz=timezone.utc)
    else:
        opened = datetime.fromisoformat(str(body.opened_at_utc).replace("Z","")).astimezone(timezone.utc)

    row = (
        body.ticket, body.symbol, body.direction, body.lot,
        body.entry_price, opened.isoformat(), body.status, body.magic
    )

    with conn() as c, c.cursor() as cur:
        execute_values(cur,
            """insert into public.trades
               (ticket,symbol,direction,lot,entry_price,opened_at_utc,status,magic)
               values %s
               on conflict (ticket) do nothing""",
            [row]
        )
    return {"ok": True}
