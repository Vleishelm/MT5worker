@app.post("/webhook/trade")
async def trade(req: Request):
    raw = await req.body()

    try:
        # decode bytes naar string
        txt = raw.decode("utf-8").strip()

        # sommige MT5 builds sturen trailing null chars → strip ze
        txt = txt.replace("\x00", "")

        # parse JSON
        p = json.loads(txt)
    except Exception as e:
        return {"status": "error", "type": "json_parse", "err": str(e), "raw": txt}

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

    conn = await get_conn()
    try:
        await conn.execute(sql,
            t.get("ticket"),
            t.get("symbol"),
            t.get("direction"),
            t.get("lot"),
            t.get("entry_price"),
            t.get("opened_at_utc"),
            t.get("status"),
            t.get("magic"),
        )
        return {"status":"ok"}
    except Exception as e:
        return {"status":"db_error","err":str(e),"payload":t}
    finally:
        await conn.close()
