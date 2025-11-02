from fastapi import FastAPI, Request
import os, json, ssl, datetime, asyncpg

app = FastAPI()

# ---------- DB connectie via losse env vars ----------
def _db_env():
    host = os.getenv("DB_HOST", "").strip()
    port = int(os.getenv("DB_PORT", "5432").strip())
    name = os.getenv("DB_NAME", "postgres").strip()
    user = os.getenv("DB_USER", "postgres").strip()
    pwd  = os.getenv("DB_PASSWORD", "").strip()
    if not host or not pwd:
        raise RuntimeError("DB env vars missing")
    return host, port, name, user, pwd

async def get_conn():
    host, port, name, user, pwd = _db_env()
    ctx = ssl.create_default_context()
    return await asyncpg.connect(host=host, port=port, user=user, password=pwd, database=name, ssl=ctx)

# ---------- Health ----------
@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/healthz_db")
async def healthz_db():
    try:
        c = await get_conn()
        await c.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "err": str(e)}

# Debug: laat zien wat de app leest (zonder wachtwoord)
@app.get("/debug/dbinfo")
def dbinfo():
    try:
        host, port, name, user, _ = _db_env()
        return {"host": host, "port": port, "db": name, "user": user}
    except Exception as e:
        return {"err": str(e)}

# ---------- Trade ingest ----------
@app.post("/webhook/trade")
async def webhook_trade(req: Request):
    raw = await req.body()
    try:
        txt = raw.decode("utf-8", "ignore").replace("\x00", "").strip()
        payload = json.loads(txt)
    except Exception as e:
        return {"status":"json_error","err":str(e)}

    t = payload.get("trade", {})
    sql = """
    insert into trades(ticket, symbol, direction, lot, entry_price, opened_at_utc, status, magic)
    values($1,$2,$3,$4,$5,$6,$7,$8)
    on conflict (ticket) do update set
      symbol=excluded.symbol, direction=excluded.direction, lot=excluded.lot,
      entry_price=excluded.entry_price, opened_at_utc=excluded.opened_at_utc,
      status=excluded.status, magic=excluded.magic;
    """
    c = await get_conn()
    try:
        await c.execute(sql,
            t.get("ticket"), t.get("symbol"), t.get("direction"),
            t.get("lot"), t.get("entry_price"), t.get("opened_at_utc"),
            t.get("status"), t.get("magic"),
        )
        return {"status":"ok"}
    except Exception as e:
        return {"status":"db_error","err":str(e),"payload":t}
    finally:
        await c.close()

# ---------- Demo insert ----------
@app.get("/webhook/demo")
async def webhook_demo():
    sql = """
    insert into trades(ticket, symbol, direction, lot, entry_price, opened_at_utc, status, magic)
    values($1,$2,$3,$4,$5,$6,$7,$8)
    on conflict (ticket) do update set
      symbol=excluded.symbol, direction=excluded.direction, lot=excluded.lot,
      entry_price=excluded.entry_price, opened_at_utc=excluded.opened_at_utc,
      status=excluded.status, magic=excluded.magic;
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"
    c = await get_conn()
    try:
        await c.execute(sql, 99999, "XAUUSD", "buy", 0.1, 2000.0, now, "open", 55)
        return {"status":"ok"}
    finally:
        await c.close()
