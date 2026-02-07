# NBA API — Oddsfield Integration Guide

> **For**: Another AI integrating this into the Oddsfield sports betting dashboard.
> **Repo**: Local clone of [`swar/nba_api`](https://github.com/swar/nba_api) v1.11.3

---

## 1. Is this the standard `nba_api` pip package, or custom code?

**This IS the `nba_api` pip package itself.** This repo is the source code for it.

```
pip install nba_api   # installs exactly this code
```

It is **not** a wrapper around the pip package. It **is** the pip package. There is no custom application code, no web server, no database. It is a pure client library that makes HTTP GET requests to two NBA.com backends:

| Backend | Base URL | Use case |
|---|---|---|
| **Stats API** | `https://stats.nba.com/stats/{endpoint}` | Historical/tabular data, date-specific scoreboards |
| **Live API** | `https://cdn.nba.com/static/json/liveData/{endpoint}` | Real-time today's scores, live box scores, play-by-play |

The library adds value over raw HTTP in these ways:
- Browser-mimicking headers (NBA.com blocks requests without them)
- `requests.Session` pooling (reused across calls)
- Proxy rotation support (pass a list, one is randomly picked per request)
- 140+ endpoint classes with typed parameters
- Response parsing into dicts, JSON, or pandas DataFrames
- Offline static data for team/player lookups (no network call)
- V3 endpoint parsers that flatten nested JSON into tabular format

**No authentication required.** No API keys, no tokens, no OAuth. The NBA.com APIs are public.

---

## 2. Exact code to get today's live scoreboard

### The call

```python
from nba_api.live.nba.endpoints import ScoreBoard

scoreboard = ScoreBoard()  # fetches immediately, no params needed
games = scoreboard.games.get_dict()  # list of game dicts
```

That's it. One import, one constructor, one accessor. Under the hood this hits:
```
GET https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json
```

### Parsing every field Oddsfield needs

```python
from nba_api.live.nba.endpoints import ScoreBoard
import re

scoreboard = ScoreBoard()

for game in scoreboard.games.get_dict():

    # --- GAME STATUS ---
    # gameStatus is the integer you branch on:
    #   1 = not started (upcoming)
    #   2 = in progress (live)
    #   3 = final
    status_int = game["gameStatus"]          # 1, 2, or 3
    status_text = game["gameStatusText"]     # "7:00 pm ET", "Q3 05:22", "Half", "Final", "Final/OT"

    # Halftime detection — there is NO dedicated status code for halftime.
    # It shows up as gameStatus=2 with gameStatusText containing "Half".
    is_halftime = (status_int == 2 and "Half" in status_text)

    # --- SCORES ---
    home_score = game["homeTeam"]["score"]   # int, 0 before tipoff
    away_score = game["awayTeam"]["score"]   # int, 0 before tipoff

    # Per-quarter scores:
    # game["homeTeam"]["periods"] -> [{"period": 1, "periodType": "REGULAR", "score": 28}, ...]
    # Empty list before tipoff.

    # --- QUARTER / PERIOD ---
    period = game["period"]                  # int: 1-4 = Q1-Q4, 5 = OT1, 6 = OT2, etc.
                                             # 0 before tipoff

    # --- GAME CLOCK ---
    raw_clock = game["gameClock"]            # "PT05M22.00S" during play
                                             # "" (empty string) before tipoff
                                             # "PT00M00.00S" at end of period/game

    # Parse to minutes:seconds
    def parse_clock(clock_str):
        """Parse 'PT05M22.00S' -> '5:22'. Returns '' for empty/pre-game."""
        if not clock_str:
            return ""
        m = re.match(r"PT(\d+)M([\d.]+)S", clock_str)
        if not m:
            return ""
        mins = int(m.group(1))
        secs = int(float(m.group(2)))
        return f"{mins}:{secs:02d}"

    clock_display = parse_clock(raw_clock)   # "5:22" or ""

    # --- TEAM IDENTIFIERS ---
    # Every game gives you ALL THREE forms for both teams:
    home_id      = game["homeTeam"]["teamId"]       # 1610612738 (int)
    home_tricode = game["homeTeam"]["teamTricode"]   # "BOS" (3-letter string)
    home_name    = game["homeTeam"]["teamName"]      # "Celtics"
    home_city    = game["homeTeam"]["teamCity"]       # "Boston"

    away_id      = game["awayTeam"]["teamId"]
    away_tricode = game["awayTeam"]["teamTricode"]
    away_name    = game["awayTeam"]["teamName"]
    away_city    = game["awayTeam"]["teamCity"]

    # --- GAME ID (for drill-down to box score / play-by-play) ---
    game_id = game["gameId"]                 # "0022500780"

    # --- OTHER USEFUL FIELDS ---
    game_time_utc = game["gameTimeUTC"]      # "2026-02-07T00:30:00Z"
    game_time_et  = game["gameEt"]           # "2026-02-06T19:30:00-05:00"
    home_record   = f"{game['homeTeam']['wins']}-{game['homeTeam']['losses']}"
    away_record   = f"{game['awayTeam']['wins']}-{game['awayTeam']['losses']}"
```

### What the raw response looks like

Here is the exact structure of one game object from `scoreboard.games.get_dict()`, taken from the `expected_data` schema in `src/nba_api/live/nba/endpoints/scoreboard.py:7-78`:

```json
{
    "gameId": "0022500780",
    "gameCode": "20260207/BOSCLE",
    "gameStatus": 2,
    "gameStatusText": "Q3 05:22",
    "period": 3,
    "gameClock": "PT05M22.00S",
    "gameTimeUTC": "2026-02-07T00:30:00Z",
    "gameEt": "2026-02-06T19:30:00-05:00",
    "regulationPeriods": 4,
    "seriesGameNumber": "",
    "seriesText": "",
    "homeTeam": {
        "teamId": 1610612739,
        "teamName": "Cavaliers",
        "teamCity": "Cleveland",
        "teamTricode": "CLE",
        "wins": 38,
        "losses": 12,
        "score": 78,
        "inBonus": null,
        "timeoutsRemaining": 4,
        "periods": [
            {"period": 1, "periodType": "REGULAR", "score": 28},
            {"period": 2, "periodType": "REGULAR", "score": 31},
            {"period": 3, "periodType": "REGULAR", "score": 19}
        ]
    },
    "awayTeam": {
        "teamId": 1610612738,
        "teamName": "Celtics",
        "teamCity": "Boston",
        "teamTricode": "BOS",
        "wins": 35,
        "losses": 15,
        "score": 72,
        "inBonus": null,
        "timeoutsRemaining": 3,
        "periods": [
            {"period": 1, "periodType": "REGULAR", "score": 25},
            {"period": 2, "periodType": "REGULAR", "score": 27},
            {"period": 3, "periodType": "REGULAR", "score": 20}
        ]
    },
    "gameLeaders": {
        "homeLeaders": {
            "personId": 1628386,
            "name": "Donovan Mitchell",
            "jerseyNum": "45",
            "position": "SG",
            "teamTricode": "CLE",
            "playerSlug": null,
            "points": 22,
            "rebounds": 4,
            "assists": 6
        },
        "awayLeaders": {
            "personId": 1628369,
            "name": "Jayson Tatum",
            "jerseyNum": "0",
            "position": "SF",
            "teamTricode": "BOS",
            "playerSlug": null,
            "points": 19,
            "rebounds": 7,
            "assists": 5
        }
    },
    "pbOdds": {"team": null, "odds": 0.0, "suspended": 0}
}
```

For a **pre-game** (gameStatus=1) game, the differences are:
- `gameStatus`: `1`
- `gameStatusText`: `"7:00 pm ET"` (tip-off time as a display string)
- `period`: `0`
- `gameClock`: `""` (empty string)
- `score`: `0` on both teams
- `periods`: `[]` (empty list) on both teams
- `gameLeaders`: all fields are `0` / `""` / `null`
- `inBonus`: `null`
- `timeoutsRemaining`: `0`

---

## 3. How to match NBA games to external data sources

The live scoreboard gives you **three identifiers per team** on every game object:

| Field | Example | Best for matching to... |
|---|---|---|
| `teamId` | `1610612738` | NBA's internal ID. Stable across seasons. **Best primary key for NBA-to-NBA joins.** |
| `teamTricode` | `"BOS"` | 3-letter code. **Best for matching to sportsbooks/odds APIs** which almost universally use tricodes. |
| `teamName` | `"Celtics"` | Nickname only (not city). Useful for display. |
| `teamCity` | `"Boston"` | City only. |

**For Oddsfield, use `teamTricode` to match games to odds feeds.** It's the most universal cross-platform identifier. Most sportsbook APIs (DraftKings, FanDuel, BetMGM, etc.) use the same 3-letter codes.

If you need to convert between them offline (no network call):

```python
from nba_api.stats.static import teams

# tricode -> ID
celtics = teams.find_team_by_abbreviation("BOS")
# Returns: {"id": 1610612738, "full_name": "Boston Celtics",
#           "abbreviation": "BOS", "nickname": "Celtics",
#           "city": "Boston", "state": "Massachusetts", "year_founded": 1946}

# ID -> everything
celtics = teams.find_team_name_by_id(1610612738)
# Returns same dict as above

# Fuzzy search by name
teams.find_teams_by_full_name("Celtics")      # regex search, returns list
teams.find_teams_by_city("Boston")             # regex search, returns list
teams.find_teams_by_nickname("Celtics")        # regex search, returns list
```

There is also a `gameId` per game (`"0022500780"`) which is the best key for joining scoreboard data to box scores and play-by-play within this API.

---

## 4. Gotchas and edge cases

### gameClock format is NOT always `PT##M##.##S`

| Situation | `gameClock` value | How to handle |
|---|---|---|
| Mid-play | `"PT05M22.00S"` | Normal — parse with regex |
| End of quarter / end of game | `"PT00M00.00S"` | Clock at zero. Check `period` and `gameStatus` to know why. |
| Pre-game (gameStatus=1) | `""` (empty string) | **Critical gotcha.** Your parser MUST handle empty string. |
| Between quarters | `"PT00M00.00S"` | Same as end-of-quarter. `gameStatus` is still `2`. |

**Your clock parser must handle `""`.** The `expected_data` in `scoreboard.py:20` explicitly defines the default as `"gameClock": ""`.

### Halftime is invisible at the status-code level

There is no `gameStatus=4` for halftime. It's `gameStatus=2` (still "in progress") with `gameStatusText` containing `"Half"`. You must string-match:

```python
is_halftime = (game["gameStatus"] == 2 and "Half" in game["gameStatusText"])
```

### Overtime handling

- `period` goes to `5` for OT1, `6` for OT2, etc.
- `regulationPeriods` is always `4` (tells you where regulation ends)
- `gameStatusText` becomes `"OT1 05:00"` etc.
- `periods` array in team data will have entries with `"periodType": "OVERTIME"`
- A game can theoretically have unlimited OT periods

```python
is_overtime = game["period"] > game["regulationPeriods"]
```

### Games spanning midnight (ET)

The live scoreboard endpoint is `todaysScoreboard_00.json` — it returns games for **today's NBA calendar date**, which is based on Eastern Time. A 10:30 PM ET tip-off that goes to midnight will stay on the same scoreboard until it finishes. This is not a problem for polling — the game stays in the response until it's final.

However: if you poll at 1:00 AM ET, you'll get **tomorrow's** empty scoreboard (or tomorrow's early games), and any just-finished late games from "yesterday" will be gone. If you need historical results, use `ScoreboardV3(game_date="2026-02-06")` instead.

### Pre-game null/empty fields

When `gameStatus == 1`:
- `score` = `0` (int, not null) on both teams
- `period` = `0` (int)
- `gameClock` = `""` (empty string, NOT null, NOT "PT00M00.00S")
- `periods` = `[]` (empty list, not null)
- `inBonus` = `null`
- `timeoutsRemaining` = `0`
- `gameLeaders` fields are all zeroed: `personId=0`, `name=""`, `points=0`, etc.

### Error handling — the library swallows HTTP errors

**Critical for production.** Look at `src/nba_api/library/http.py:159-169`:

```python
response = self.get_session().get(
    url=base_url,
    params=parameters,
    headers=request_headers,
    proxies=proxies,
    timeout=timeout,
)
url = response.url
status_code = response.status_code
contents = response.text
```

The library **does not check `status_code`**. A 403, 429, or 500 will be stored as-is. Then `clean_contents` in both HTTP subclasses replaces the NBA error JSON with XML:

```python
# src/nba_api/live/nba/library/http.py:23-25
def clean_contents(self, contents):
    if '{"Message":"An error has occurred."}' in contents:
        return "<Error><Message>An error has occurred.</Message></Error>"
    return contents
```

This means calling `.get_dict()` on an error response **will throw a `json.JSONDecodeError`** (because it's now XML). The `raise_exception_on_error` parameter exists but defaults to `False` and is never passed by any endpoint class.

**You must wrap calls in try/except:**

```python
try:
    scoreboard = ScoreBoard(timeout=10)
    games = scoreboard.games.get_dict()
except Exception:
    # Network error, NBA.com down, rate limited, bad JSON, etc.
    games = []
```

### No retry or rate limiting built in

Confirmed by searching the entire `src/` tree: there are zero instances of `time.sleep`, `retry`, `backoff`, `rate_limit`, or `throttle`. You must implement your own.

### ScoreboardV2 is broken

Do NOT use `ScoreboardV2` for the 2025-26 season — line score data is broken. Use the **live** `ScoreBoard` for real-time, or `ScoreboardV3` for date-specific queries.

### PlayByPlayV2 returns empty

Use `PlayByPlayV3` (stats API) or the live `PlayByPlay` endpoint instead.

---

## 5. Minimum code to poll live scores every 60 seconds

```python
"""Minimal live NBA score poller for Oddsfield."""

import re
import time
from nba_api.live.nba.endpoints import ScoreBoard


def parse_clock(clock_str):
    """'PT05M22.00S' -> '5:22'. Empty string -> ''."""
    if not clock_str:
        return ""
    m = re.match(r"PT(\d+)M([\d.]+)S", clock_str)
    if not m:
        return clock_str  # return raw if unparseable
    return f"{int(m.group(1))}:{int(float(m.group(2))):02d}"


def get_game_state(game):
    """Extract a normalized game state dict from a raw scoreboard game."""
    status = game["gameStatus"]
    status_text = game["gameStatusText"]

    if status == 1:
        state = "upcoming"
    elif status == 3:
        state = "final"
    elif status == 2 and "Half" in status_text:
        state = "halftime"
    elif status == 2:
        state = "live"
    else:
        state = "unknown"

    return {
        "game_id":       game["gameId"],
        "state":         state,
        "status_text":   status_text,
        "period":        game["period"],
        "clock":         parse_clock(game["gameClock"]),
        "is_overtime":   game["period"] > game["regulationPeriods"],
        "home_tricode":  game["homeTeam"]["teamTricode"],
        "home_team_id":  game["homeTeam"]["teamId"],
        "home_name":     f"{game['homeTeam']['teamCity']} {game['homeTeam']['teamName']}",
        "home_score":    game["homeTeam"]["score"],
        "away_tricode":  game["awayTeam"]["teamTricode"],
        "away_team_id":  game["awayTeam"]["teamId"],
        "away_name":     f"{game['awayTeam']['teamCity']} {game['awayTeam']['teamName']}",
        "away_score":    game["awayTeam"]["score"],
        "game_time_utc": game["gameTimeUTC"],
    }


def poll_scores():
    """Poll live scores forever. Yields list of game states each cycle."""
    while True:
        try:
            scoreboard = ScoreBoard(timeout=10)
            games = scoreboard.games.get_dict()
            yield [get_game_state(g) for g in games]
        except Exception as e:
            print(f"Error fetching scoreboard: {e}")
            yield []
        time.sleep(60)


# Usage:
if __name__ == "__main__":
    for game_states in poll_scores():
        for g in game_states:
            print(f"[{g['state']:>9}] {g['away_tricode']} {g['away_score']:>3} "
                  f"@ {g['home_tricode']} {g['home_score']:>3}  "
                  f"{'OT' + str(g['period'] - 4) if g['is_overtime'] else 'Q' + str(g['period']) if g['period'] > 0 else ''} "
                  f"{g['clock']}")
        print("---")
```

**Important notes for production:**
- Each `ScoreBoard()` call is a single HTTP GET. The CDN response is typically ~5-15KB.
- The CDN updates roughly every 10-15 seconds during live games. Polling faster than 30s is wasteful.
- For a betting dashboard, 60s is fine for score display. If you need sub-minute for live betting triggers, poll every 15-30s.
- The `requests.Session` is reused automatically across calls (class-level singleton at `NBAHTTP._session`).
- If you need more detail on a specific game during play, call `BoxScore(game_id=game_id)` — same live API, game-specific.

---

## 6. Does this repo store any data in a database?

**No.** Confirmed by searching the entire `src/` tree for `sqlite`, `postgres`, `mysql`, `mongo`, `database`, `db_`, `.db`, `engine =`, `Session(`, `create_all`, and `CREATE TABLE`. The only hit is `requests.Session()` in the HTTP layer (connection pooling, not database).

This is a **pure stateless client library**. Every call is a fresh HTTP GET. There is:
- No caching layer
- No local storage
- No persistence
- No write operations

The only "stored" data is the bundled static player/team lookup tables in `src/nba_api/stats/library/data.py` (~360KB of hardcoded Python lists). These are read-only and baked into the package at release time.

If Oddsfield needs to cache/store NBA data, that's entirely your responsibility. The library will happily re-fetch the same data on every call.
