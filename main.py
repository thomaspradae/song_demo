from fastapi import FastAPI, Request
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

# Load songs
with open("songs.json", "r") as f:
    songs = json.load(f)

# Initialize ratings
for s in songs:
    s["elo"] = 1000.0
    s["matches"] = 0
    s["sigma"] = 350.0  # initial uncertainty

K = 32  # ELO constant
SIGMA_DECAY = 0.97  # how fast uncertainty drops per match


def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_bayesian_elo(winner, loser):
    Ea = expected_score(winner["elo"], loser["elo"])
    Eb = 1 - Ea

    winner["elo"] += K * (1 - Ea)
    loser["elo"] += K * (0 - Eb)

    # Update matches
    winner["matches"] += 1
    loser["matches"] += 1

    # Reduce uncertainty as more matches are played
    winner["sigma"] = max(50, winner["sigma"] * SIGMA_DECAY)
    loser["sigma"] = max(50, loser["sigma"] * SIGMA_DECAY)


@app.get("/pair")
def get_pair():
    a, b = random.sample(songs, 2)
    return {"songA": a, "songB": b}


@app.post("/vote")
async def vote(request: Request):
    data = await request.json()
    winner_id = data["winner_id"]
    loser_id = data["loser_id"]

    winner = next(s for s in songs if s["id"] == winner_id)
    loser = next(s for s in songs if s["id"] == loser_id)
    update_bayesian_elo(winner, loser)

    return {"message": "Vote recorded"}


@app.get("/leaderboard")
def leaderboard():
    sorted_songs = sorted(songs, key=lambda s: s["elo"], reverse=True)
    total_matches = sum(s["matches"] for s in songs)
    return JSONResponse({
        "total_matches": total_matches,
        "songs": sorted_songs
    })


@app.get("/vote_page", response_class=HTMLResponse)
def vote_page():
    with open("static/vote.html") as f:
        return HTMLResponse(f.read())


@app.get("/leaderboard_page", response_class=HTMLResponse)
def leaderboard_page():
    with open("static/leaderboard.html") as f:
        return HTMLResponse(f.read())

@app.post("/reset")
def reset_votes():
    for song in songs:
        song["score"] = 0
    return {"status": "reset"}