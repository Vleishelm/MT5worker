from fastapi import FastAPI, Request
from supabase import create_client
import os

app = FastAPI()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/trade")
async def trade(request: Request):
    data = await request.json()
    supabase.table("trades").insert(data).execute()
    return {"status": "saved"}
