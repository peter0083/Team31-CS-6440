import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="Receiver Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_data = []

@app.post("/receive")
async def receive_data(request: Request):
    global latest_data
    latest_data = await request.json()
    logging.info(f"📦 Received {len(latest_data)} studies from MS1")
    return {"status": "received", "count": len(latest_data)}

@app.get("/display")
async def display_data():
    return latest_data or {"message": "No data received yet."}
