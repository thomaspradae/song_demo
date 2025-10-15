# main.py
import os
import random
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Load songs from songs.json once at startup
with open("songs.json", "r") as f:
    songs = json.load(f)

# Configurable constants
INITIAL_ELO = 1000.0
INITIAL_SIGMA = 350.0
MIN_SIGMA = 50.0
K = 32  # ELO K-factor
SIGMA_DECAY = 0.97  # reduce sigma per match

def reset_elo():
    """Reset elo, matches, and sigma for all songs to initial values."""
    for s in songs:
        s["elo"] = float(s.get("elo", INITIAL_ELO))  # if already present, reset anyway
        s["elo"] = INITIAL_ELO
        s["matches"] = 0
        s["sigma"] = INITIAL_SIGMA

# initialize on start
reset_elo()

def expected_score(rating_a, rating_b):
    """Standard ELO expected score."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

def update_bayesian_elo(winner, loser):
    """Update winner and loser elo, matches and sigma."""
    Ea = expected_score(winner["elo"], loser["elo"])
    Eb = 1.0 - Ea

    winner["elo"] += K * (1.0 - Ea)
    loser["elo"] += K * (0.0 - Eb)

    # Update matches counters
    winner["matches"] += 1
    loser["matches"] += 1

    # Reduce uncertainty (sigma) as matches increase
    winner["sigma"] = max(MIN_SIGMA, winner.get("sigma", INITIAL_SIGMA) * SIGMA_DECAY)
    loser["sigma"] = max(MIN_SIGMA, loser.get("sigma", INITIAL_SIGMA) * SIGMA_DECAY)

@app.get("/pair")
def get_pair():
    """Return two random distinct songs (full objects)."""
    a, b = random.sample(songs, 2)
    return {"songA": a, "songB": b}

@app.post("/vote")
async def vote(request: Request):
    """Receive winner_id and loser_id (integers) in JSON and update ratings."""
    data = await request.json()
    winner_id = data.get("winner_id")
    loser_id = data.get("loser_id")
    if winner_id is None or loser_id is None:
        return JSONResponse({"error": "winner_id and loser_id required"}, status_code=400)

    winner = next((s for s in songs if s["id"] == winner_id), None)
    loser = next((s for s in songs if s["id"] == loser_id), None)
    if winner is None or loser is None:
        return JSONResponse({"error": "invalid id"}, status_code=400)

    update_bayesian_elo(winner, loser)
    return {"message": "Vote recorded"}

@app.get("/leaderboard")
def leaderboard():
    """Return leaderboard JSON including total matches and sorted songs list."""
    sorted_songs = sorted(songs, key=lambda s: s["elo"], reverse=True)
    total_matches = sum(s.get("matches", 0) for s in songs)
    return JSONResponse({"total_matches": total_matches, "songs": sorted_songs})

@app.post("/reset")
def reset_votes():
    """Reset elo/matches/sigma to initial values."""
    reset_elo()
    return {"status": "reset", "message": "ELO, matches and sigma reset to initial values."}

@app.get("/vote_page", response_class=HTMLResponse)
def vote_page():
    with open("static/vote.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/leaderboard_page", response_class=HTMLResponse)
def leaderboard_page():
    with open("static/leaderboard.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
