from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PL Live API", version="1.0.0")

# Allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev: open CORS for sandbox
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "pl-live"}


# Simple mock fixtures (ids match the frontend for demo)
FIXTURE_IDS = ["pl-001", "pl-002", "pl-003"]
FIXTURE_META = {
    "pl-001": {"home": "Manchester City", "away": "Liverpool"},
    "pl-002": {"home": "Arsenal", "away": "Tottenham"},
    "pl-003": {"home": "Chelsea", "away": "Manchester United"},
}


@app.get("/fixtures")
async def fixtures():
    now = datetime.utcnow().isoformat()
    return [
        {
            "id": fid,
            "home": FIXTURE_META[fid]["home"],
            "away": FIXTURE_META[fid]["away"],
            "kickoff": now,
            "venue": "TBD",
        }
        for fid in FIXTURE_IDS
    ]


def _initial_state(fid: str) -> dict:
    return {
        "id": fid,
        "status": "LIVE",
        "minute": random.randint(1, 5),
        "scoreHome": 0,
        "scoreAway": 0,
        "xgHome": round(random.uniform(0.2, 0.6), 2),
        "xgAway": round(random.uniform(0.1, 0.5), 2),
        "shotsHome": random.randint(1, 4),
        "shotsAway": random.randint(0, 3),
        "possessionHome": random.randint(40, 60),
        "home": FIXTURE_META[fid]["home"],
        "away": FIXTURE_META[fid]["away"],
    }


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await websocket.accept()

    # Per-connection state for all fixtures
    state = {fid: _initial_state(fid) for fid in FIXTURE_IDS}
    try:
        while True:
            # Update each fixture a bit and send individual messages
            for fid in FIXTURE_IDS:
                s = state[fid]
                # Advance clock
                s["minute"] = min(95, s["minute"] + random.randint(1, 2))
                # Random chance of a goal
                if random.random() < 0.12:
                    if random.random() < 0.5:
                        s["scoreHome"] += 1
                        s["xgHome"] = round(s["xgHome"] + random.uniform(0.05, 0.2), 2)
                        s["shotsHome"] += random.randint(1, 2)
                    else:
                        s["scoreAway"] += 1
                        s["xgAway"] = round(s["xgAway"] + random.uniform(0.05, 0.2), 2)
                        s["shotsAway"] += random.randint(1, 2)
                # Small metric drift
                s["xgHome"] = round(s["xgHome"] + random.uniform(0.0, 0.05), 2)
                s["xgAway"] = round(s["xgAway"] + random.uniform(0.0, 0.05), 2)
                s["shotsHome"] += random.choice([0, 0, 1])
                s["shotsAway"] += random.choice([0, 0, 1])
                s["possessionHome"] = max(35, min(65, s["possessionHome"] + random.choice([-1, 0, 1])))

                await websocket.send_json(s)

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        # Client disconnected; simply exit
        return
