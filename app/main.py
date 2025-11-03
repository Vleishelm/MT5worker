# app/main.py
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, requests

SB_URL = os.environ["SUPABASE_URL"].rstrip("/")
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
HEAD = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

class Payload(BaseModel):
    trade_uid:str; broker:str; account_id:str; symbol:str; magic:int; direction:str
    open_time:str; open_price:float; volume_lots:float
    close_time:str|None=None; close_price:float|None=None
    commission:float=0; swap:float=0; profit:float|None=None
    sl:float|None=None; tp:float|None=None; grid_leg:int=0; comment:str|None=None
    indicators:dict|None=None

@app.post("/mt5/trade")
def ingest(p: Payload, authorization: str = Header(default="")):
    if authorization != f"Bearer {INGEST_TOKEN}":
        raise HTTPException(401, "unauthorized")

    tr = p.model_dump()
    ind = tr.pop("indicators", None)

    r = requests.post(
        f"{SB_URL}/rest/v1/trades",
        headers=HEAD, json=[tr],
        params={"on_conflict":"trade_uid","return":"minimal"}
    )
    if r.status_code >= 300:
        raise HTTPException(500, f"trades upsert failed: {r.text}")

    if ind:
        ind_row = {"trade_uid": p.trade_uid, **ind}
        r2 = requests.post(
            f"{SB_URL}/rest/v1/trade_indicators",
            headers=HEAD, json=[ind_row],
            params={"on_conflict":"trade_uid","return":"minimal"}
        )
        if r2.status_code >= 300:
            raise HTTPException(500, f"indicators upsert failed: {r2.text}")

    return {"ok": True}
