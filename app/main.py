from fastapi import FastAPI, Request
import os, asyncpg

app = FastAPI()

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/webhook/trade")  # eerst simpel, later beveiligen
async def trade(req: Request):
    p = await req.json()
    t = p.get("trade", {})
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
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    try:
        await conn.execute(sql,
            t.get("ticket"),
            t.get("symbol"),
            t.get("direction"),
            t.get("lot"),
            t.get("entry_price"),
            t.get("opened_at_utc"),
            t.get("status"),
            t.get("magic")
        )
    finally:
        await conn.close()
    return {"status": "ok"}
