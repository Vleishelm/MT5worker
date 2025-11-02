from fastapi import FastAPI, Request
import os, ssl, json, datetime, asyncpg

app = FastAPI()

def db_url() -> str:
    u = os.getenv("DATABASE_URL")
    if not u:
        raise RuntimeError("DATABASE_URL missing")
    return u

async def get_conn():
    ctx = ssl.create_default_context()           # Supabase vereist SSL
    return await asyncpg.connect(db_url(), ssl=ctx)

@app.get("/healthz")
async def health():
    try:
        c = await get_conn()
        await c.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)}

@app.post("/webhook/trade")
async def trade(req: Request):
    # robuust JSON inlezen (MT5 kan \x00 of extra bytes sturen)
    raw = await req.body()
    try:
        txt = raw.decode("utf-8").replace("\x00", "").strip()
        payload = json.loads(txt)
    except Exception as e:
        return {"status": "error", "type": "json_parse", "err": str(e), "raw": txt if 'txt' in locals() else None}

    t = payload.get("trade", {})

    sql = """
    insert into trades(ticket, symbol, direction, lot, entry_price, opened_at_utc, status, magic)
    values($1,$2,$3,$4,$5,$6,$7,$8)
    on conflict (ticket) do update set
      symbol=excluded.symbol,
      direction=excluded.direction,
      lot=excluded.lot,
      entry_price=excluded.entry_price,
      opened_at_utc=excluded.opened_at_utc,
      status=excluded.status,
      magic=excluded.magic;
    """

    c = await get_conn()
    try:
        await c.execute(sql,
            t.get("ticket"),
            t.get("symbol"),
            t.get("direction"),
            t.get("lot"),
            t.get("entry_price"),
            t.get("opened_at_utc"),
            t.get("status"),
            t.get("magic"),
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "db_error", "err": str(e), "payload": t}
    finally:
        await c.close()

@app.get("/webhook/demo")
async def demo():
    sql = """
    insert into trades(ticket, symbol, direction, lot, entry_price, opened_at_utc, status, magic)
    values($1,$2,$3,$4,$5,$6,$7,$8)
    on conflict (ticket) do update set
      symbol=excluded.symbol,
      direction=excluded.direction,
      lot=excluded.lot,
      entry_price=excluded.entry_price,
      opened_at_utc=excluded.opened_at_utc,
      status=excluded.status,
      magic=excluded.magic;
    """
    c = await get_conn()
    try:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        await c.execute(sql, 99999, "XAUUSD", "buy", 0.10, 2000.0, now, "open", 55)
        return {"status": "ok"}
    finally:
        await c.close()
