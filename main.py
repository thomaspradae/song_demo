# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import random, json, math

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Load songs from JSON
with open("songs.json", "r") as f:
    songs = json.load(f)

# Initialize ratings
for s in songs:
    s["elo"] = 1000

K = 32  # sensitivity constant


def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_elo(winner, loser):
    Ea = expected_score(winner["elo"], loser["elo"])
    Eb = expected_score(loser["elo"], winner["elo"])
    winner["elo"] += K * (1 - Ea)
    loser["elo"] += K * (0 - Eb)


@app.get("/pair")
def get_pair():
    """Return two random distinct songs"""
    a, b = random.sample(songs, 2)
    return {"songA": a, "songB": b}


@app.post("/vote")
async def vote(request: Request):
    data = await request.json()
    winner_id = data["winner_id"]
    loser_id = data["loser_id"]

    winner = next(s for s in songs if s["id"] == winner_id)
    loser = next(s for s in songs if s["id"] == loser_id)
    update_elo(winner, loser)

    return {"message": "Vote recorded"}


@app.get("/leaderboard")
def leaderboard():
    sorted_songs = sorted(songs, key=lambda s: s["elo"], reverse=True)
    return JSONResponse(sorted_songs)


@app.get("/vote_page", response_class=HTMLResponse)
def vote_page():
    with open("static/vote.html") as f:
        return HTMLResponse(f.read())


@app.get("/leaderboard_page", response_class=HTMLResponse)
def leaderboard_page():
    with open("static/leaderboard.html") as f:
        return HTMLResponse(f.read())
