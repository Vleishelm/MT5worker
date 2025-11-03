import os
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import httpx
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL en SUPABASE_SERVICE_KEY ontbreken")

REST_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

class Snapshot(BaseModel):
    taken_at_utc: datetime
    symbol: str
    timeframe: str
    atr10: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None
    rsi: float | None = None
    ma50_dist: float | None = None
    spread_points: float | None = None
    session: str | None = None
    vol_bucket: str | None = None

class TradeIn(BaseModel):
    account_id: str
    magic: int
    symbol: str
    timeframe: str
    order_id: str
    parent_id: str | None = None
    side: str = Field(pattern="^(buy|sell)$")
    entry_time_utc: datetime
    exit_time_utc: datetime | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    volume_lots: float | None = None
    commission: float | None = None
    swap: float | None = None
    pnl_eur: float | None = None
    duration_sec: int | None = None
    snapshot: Snapshot

@app.post("/ingest/trade")
async def ingest_trade(payload: TradeIn):
    snapshot_data = payload.snapshot.dict()

    # 1) datetime → ISO8601 string
    dt = snapshot_data.get("taken_at_utc")
    if dt is not None:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        snapshot_data["taken_at_utc"] = dt.isoformat()

    async with httpx.AsyncClient(timeout=15) as client:
        # snapshot
        r1 = await client.post(f"{REST_URL}/market_snapshots", headers=HEADERS, json=[snapshot_data])
        if r1.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"snapshot insert fail: {r1.status_code} {r1.text}")
        snapshot_id = r1.json()[0]["id"]

        # 2) trade
        trade_dict = payload.dict()
        trade_dict["snapshot_id"] = snapshot_id
        trade_dict.pop("snapshot")

        for k in ("entry_time_utc", "exit_time_utc"):
            dt = trade_dict.get(k)
            if dt is not None:
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                trade_dict[k] = dt.isoformat()

        r2 = await client.post(f"{REST_URL}/trades", headers=HEADERS, json=[trade_dict])
        if r2.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"trade insert fail: {r2.status_code} {r2.text}")

    return {"ok": True, "trade": r2.json()[0]}
