import pathfix  # noqa — must be first

import os
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from scraper import run_scan
from db import get_all_scholarships, get_existing, delete_expired
from datetime import date
import uvicorn

app = FastAPI(title="Scholarship API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

API_KEY = os.getenv("SCRAPER_API_KEY", "change-this-secret-key")


def verify_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/")
def root():
    return {"status": "running", "today": date.today().isoformat()}


@app.get("/scholarships")
def list_scholarships():
    """Public — returns active scholarships only, soonest deadline first."""
    scholarships = get_all_scholarships(filter_expired=True)
    return {"count": len(scholarships), "as_of": date.today().isoformat(), "scholarships": scholarships}


@app.get("/scholarships/all")
def list_all():
    """Debug — returns all scholarships including expired."""
    scholarships = get_all_scholarships(filter_expired=False)
    return {"count": len(scholarships), "scholarships": scholarships}


@app.get("/scholarships/{name}")
def get_one(name: str):
    s = get_existing(name)
    if not s:
        raise HTTPException(status_code=404, detail=f"'{name}' not found")
    return s


@app.post("/scrape")
async def trigger_scan(background_tasks: BackgroundTasks, _: str = Depends(verify_key)):
    """Protected — triggers a background scan. Needs header: x-api-key"""
    background_tasks.add_task(run_scan)
    return {"status": "scan started", "sources": 77}


@app.delete("/scholarships/expired")
def remove_expired(_: str = Depends(verify_key)):
    """Protected — manually removes expired scholarships."""
    count = delete_expired(date.today().isoformat())
    return {"removed": count}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
