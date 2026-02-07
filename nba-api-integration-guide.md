# NBA API Integration Guide

> **Audience**: AI agents or developers integrating this library into another project.
> **Source repo**: <https://github.com/swar/nba_api> — version **1.11.3**

---

## 1. Architecture Overview

| Attribute | Value |
|---|---|
| **Language** | Python 3.10+ |
| **Package type** | Pure-Python client library (not a web server) |
| **Data source** | Official NBA.com APIs — no API key, no RapidAPI |
| **HTTP layer** | `requests` library with persistent `Session` pooling |
| **Build system** | Poetry (`pyproject.toml`) |
| **License** | MIT |

The library wraps **two distinct NBA backends**:

| Backend | Base URL | Purpose |
|---|---|---|
| **Stats API** | `https://stats.nba.com/stats/{endpoint}` | Historical / tabular data (140+ endpoints) |
| **Live API** | `https://cdn.nba.com/static/json/liveData/{endpoint}` | Real-time game data (4 endpoints) |

There is also an offline **static data** module for player/team lookups that requires no network calls.

---

## 2. Authentication

**None.** The NBA.com APIs are public. The library authenticates by sending browser-like headers:

```python
# Stats API headers (src/nba_api/stats/library/http.py)
STATS_HEADERS = {
    "Host": "stats.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://stats.nba.com/",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Sec-Ch-Ua": '"Chromium";v="140", "Google Chrome";v="140", "Not;A=Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "empty",
}

# Live API headers (src/nba_api/live/nba/library/http.py)
STATS_HEADERS = {
    "Host": "cdn.nba.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}
```

All endpoints accept optional `proxy`, `headers`, and `timeout` parameters to override defaults.

---

## 3. Dependencies

From `pyproject.toml`:

```
requests   >=2.32.3, <3.0.0    # HTTP client (required)
numpy      >=1.26.0             # Array handling (required; >=2.1.0 for Python 3.13+)
pandas     >=2.1.0              # DataFrame support (required; >=2.2.0 for Python 3.12+)
```

Dev-only: `pytest`, `pytest-cov`, `flake8`, `pylint`, `isort`, `python-semantic-release`.

Install:
```bash
pip install nba_api
```

---

## 4. Key Endpoints & Functions

### 4.1 Live API — Real-Time Game Data

All live endpoints are in `nba_api.live.nba.endpoints`.

#### 4.1.1 `ScoreBoard` — Today's Games / Live Scoreboard

**This is the primary endpoint for getting current game scores, status, and clock.**

```python
# src/nba_api/live/nba/endpoints/scoreboard.py

from nba_api.live.nba.endpoints import ScoreBoard

class ScoreBoard(Endpoint):
    endpoint_url = "scoreboard/todaysScoreboard_00.json"

    def __init__(self, proxy=None, headers=None, timeout=30, get_request=True):
        ...
```

**No parameters required** — automatically returns today's games.

**Attributes after fetch:**
- `score_board_date` — string, e.g. `"2026-02-07"`
- `games` — `DataSet` containing a list of game dicts

**Access methods:**
```python
scoreboard = ScoreBoard()
scoreboard.games.get_dict()   # list of game dicts
scoreboard.games.get_json()   # JSON string
scoreboard.get_dict()         # full raw response dict
scoreboard.get_json()         # full raw response JSON
```

**Example response payload** (single game from `scoreboard.games.get_dict()`):
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

**Game status codes:**
| `gameStatus` | `gameStatusText` examples | Meaning |
|---|---|---|
| `1` | `"7:30 pm ET"`, `"Pre Game"` | Not started / upcoming |
| `2` | `"Q1 08:44"`, `"Q3 05:22"`, `"Half"`, `"OT1 03:15"` | In progress |
| `3` | `"Final"`, `"Final/OT"` | Completed |

**Game clock format:** ISO 8601 duration — `"PT05M22.00S"` = 5 minutes, 22 seconds remaining.

**Period values:**
| `period` | Meaning |
|---|---|
| `1`–`4` | Q1–Q4 |
| `5` | OT1 |
| `6` | OT2 |
| `7+` | Additional overtimes |

---

#### 4.1.2 `BoxScore` — Detailed Game Stats

```python
# src/nba_api/live/nba/endpoints/boxscore.py

from nba_api.live.nba.endpoints import BoxScore

class BoxScore(Endpoint):
    endpoint_url = "boxscore/boxscore_{game_id}.json"

    def __init__(self, game_id, proxy=None, headers=None, timeout=30, get_request=True):
        ...
```

**Required parameter:** `game_id` (string, e.g. `"0022500180"`)

**Attributes after fetch:**
- `game` — full game DataSet
- `game_details` — game metadata (status, clock, arena, etc.) without team data
- `arena` — arena info DataSet
- `officials` — officials list DataSet
- `home_team` — home team DataSet (includes players + statistics)
- `home_team_player_stats` — home player stats DataSet
- `home_team_stats` — home team aggregate stats DataSet
- `away_team` — away team DataSet
- `away_team_player_stats` — away player stats DataSet
- `away_team_stats` — away team aggregate stats DataSet

**Example usage:**
```python
box = BoxScore(game_id="0022500180")

# Game metadata
details = box.game_details.get_dict()
# details["gameStatus"]       -> 3
# details["gameStatusText"]   -> "Final"
# details["period"]           -> 4
# details["gameClock"]        -> "PT00M00.00S"

# Team scores
home = box.home_team_stats.get_dict()
# home["teamName"]  -> "Celtics"
# home["score"]     -> 124
# home["statistics"]["points"] -> 124

# Individual player stats
players = box.home_team_player_stats.get_dict()
# players[0]["name"]                         -> "Jaylen Brown"
# players[0]["statistics"]["points"]         -> 21
# players[0]["statistics"]["assists"]        -> 8
# players[0]["statistics"]["reboundsTotal"]  -> 2
```

**Player statistics fields** (per player in `statistics` dict):
`assists`, `blocks`, `blocksReceived`, `fieldGoalsAttempted`, `fieldGoalsMade`, `fieldGoalsPercentage`, `foulsOffensive`, `foulsDrawn`, `foulsPersonal`, `foulsTechnical`, `freeThrowsAttempted`, `freeThrowsMade`, `freeThrowsPercentage`, `minus`, `minutes` (ISO 8601), `minutesCalculated`, `plus`, `plusMinusPoints`, `points`, `pointsFastBreak`, `pointsInThePaint`, `pointsSecondChance`, `reboundsDefensive`, `reboundsOffensive`, `reboundsTotal`, `steals`, `threePointersAttempted`, `threePointersMade`, `threePointersPercentage`, `turnovers`, `twoPointersAttempted`, `twoPointersMade`, `twoPointersPercentage`

---

#### 4.1.3 `PlayByPlay` — Play-by-Play Events

```python
# src/nba_api/live/nba/endpoints/playbyplay.py

from nba_api.live.nba.endpoints import PlayByPlay

class PlayByPlay(Endpoint):
    endpoint_url = "playbyplay/playbyplay_{game_id}.json"

    def __init__(self, game_id, proxy=None, headers=None, timeout=30, get_request=True):
        ...
```

**Required parameter:** `game_id`

**Attributes after fetch:**
- `actions` — DataSet of play-by-play events

**Example action object:**
```json
{
    "actionNumber": 4,
    "clock": "PT11M58.00S",
    "timeActual": "2021-01-16T00:40:31.3Z",
    "period": 1,
    "periodType": "REGULAR",
    "teamId": 1610612738,
    "teamTricode": "BOS",
    "actionType": "jumpball",
    "subType": "recovered",
    "descriptor": "startperiod",
    "qualifiers": [],
    "personId": 1629684,
    "x": null,
    "y": null,
    "possession": 1610612738,
    "scoreHome": "0",
    "scoreAway": "0",
    "isFieldGoal": 0,
    "description": "Jump Ball T. Thompson vs. N. Vucevic: Tip to G. Williams"
}
```

Common `actionType` values: `"jumpball"`, `"2pt"`, `"3pt"`, `"freethrow"`, `"turnover"`, `"rebound"`, `"foul"`, `"substitution"`, `"timeout"`, `"violation"`, `"stoppage"`, `"period"`.

---

#### 4.1.4 `Odds` — Betting Odds

```python
# src/nba_api/live/nba/endpoints/odds.py

from nba_api.live.nba.endpoints import Odds

class Odds(Endpoint):
    endpoint_url = "odds/odds_todaysGames.json"

    def __init__(self, proxy=None, headers=None, timeout=30, get_request=True):
        ...
```

**No parameters required.** Despite the URL name, returns odds for all available games (not just today's).

**Attributes after fetch:**
- `games` — DataSet of game odds

**Example game odds object:**
```json
{
    "gameId": "0022500780",
    "sr_id": "",
    "srMatchId": "",
    "homeTeamId": "1610612739",
    "awayTeamId": "1610612738",
    "markets": [
        {
            "name": "Moneyline",
            "odds_type_id": 1,
            "group_name": "...",
            "books": [
                {
                    "id": "espn",
                    "name": "ESPN",
                    "outcomes": [
                        {"type": "home", "odds": "-150", "opening_odds": "-145", "odds_trend": ""},
                        {"type": "away", "odds": "+130", "opening_odds": "+125", "odds_trend": ""}
                    ],
                    "url": "",
                    "countryCode": ""
                }
            ]
        }
    ]
}
```

---

### 4.2 Stats API — Historical / Detailed Data

All stats endpoints are in `nba_api.stats.endpoints`. Every endpoint follows the same pattern:

```python
from nba_api.stats.endpoints import EndpointName

result = EndpointName(required_param="value", optional_param="value")

# All endpoints expose:
result.get_dict()              # raw response dict
result.get_json()              # raw response JSON string
result.get_normalized_dict()   # normalized dict (V2 endpoints only)
result.get_data_frames()       # list of DataFrames for all datasets

# Named dataset attributes (varies per endpoint):
result.dataset_name.get_dict()
result.dataset_name.get_json()
result.dataset_name.get_data_frame()  # requires pandas
```

#### 4.2.1 `ScoreboardV3` — Date-Specific Scoreboard (RECOMMENDED over V2)

```python
# src/nba_api/stats/endpoints/scoreboardv3.py

from nba_api.stats.endpoints import ScoreboardV3

class ScoreboardV3(Endpoint):
    endpoint = "scoreboardv3"

    def __init__(
        self,
        game_date,                    # Required: "YYYY-MM-DD"
        league_id=LeagueID.default,   # "00" for NBA
        proxy=None, headers=None, timeout=30, get_request=True,
    ):
        ...
```

**DataSets available:**
| Attribute | Description | Key columns |
|---|---|---|
| `scoreboard_info` | Date and league metadata | `gameDate`, `leagueId`, `leagueName` |
| `game_header` | Core game info for each game | `gameId`, `gameCode`, `gameStatus`, `gameStatusText`, `period`, `gameClock`, `gameTimeUTC`, `gameEt`, `regulationPeriods`, `seriesGameNumber`, `gameLabel`, `seriesText` |
| `line_score` | Team scores and records (2 rows per game) | `gameId`, `teamId`, `teamCity`, `teamName`, `teamTricode`, `wins`, `losses`, `score`, `inBonus`, `timeoutsRemaining` |
| `game_leaders` | Top performers per game | `gameId`, `teamId`, `leaderType`, `personId`, `name`, `jerseyNum`, `position`, `teamTricode`, `points`, `rebounds`, `assists` |
| `team_leaders` | Season leaders per team | same as game_leaders + `seasonLeadersFlag` |
| `broadcasters` | TV/radio/streaming info | `gameId`, `broadcasterType`, `broadcasterId`, `broadcastDisplay`, `broadcasterTeamId` |

**Example usage:**
```python
from nba_api.stats.endpoints import ScoreboardV3

scoreboard = ScoreboardV3(game_date="2026-02-07")

# Get all games as a DataFrame
games_df = scoreboard.game_header.get_data_frame()
scores_df = scoreboard.line_score.get_data_frame()
leaders_df = scoreboard.game_leaders.get_data_frame()
```

---

#### 4.2.2 Complete Stats Endpoint Catalog

Below is every stats endpoint file, grouped by category. All accept `proxy`, `headers`, `timeout`, `get_request` in addition to their specific parameters.

**Scoreboard & Schedule:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `ScoreboardV3` | `game_date` | Day's games, scores, status (RECOMMENDED) |
| `ScoreboardV2` | `game_date` | Legacy scoreboard (DEPRECATED — broken for 2025-26) |
| `ScheduleLeagueV2` | `season` | Full season schedule |
| `ScheduleLeagueV2Int` | `season` | International schedule |

**Player Stats:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `CommonPlayerInfo` | `player_id` | Player bio and career info |
| `PlayerCareerStats` | `player_id` | Career stats by season |
| `PlayerGameLog` | `player_id`, `season` | Game-by-game stats |
| `PlayerGameLogs` | `player_id`, `season` | Alternate game logs |
| `PlayerProfileV2` | `player_id` | Comprehensive profile |
| `PlayerDashboardByGeneralSplits` | `player_id`, `season` | Stats by split type |
| `PlayerDashboardByGameSplits` | `player_id`, `season` | Stats by game segment |
| `PlayerDashboardByClutch` | `player_id`, `season` | Clutch stats |
| `PlayerDashboardByLastNGames` | `player_id`, `season` | Last N games |
| `PlayerDashboardByShootingSplits` | `player_id`, `season` | Shooting breakdown |
| `PlayerDashboardByTeamPerformance` | `player_id`, `season` | By team performance |
| `PlayerDashboardByYearOverYear` | `player_id`, `season` | Year-over-year |
| `PlayerDashPtPass` | `player_id`, `season` | Passing tracking |
| `PlayerDashPtReb` | `player_id`, `season` | Rebounding tracking |
| `PlayerDashPtShots` | `player_id`, `season` | Shot tracking |
| `PlayerDashPtShotDefend` | `player_id`, `season` | Defensive shot tracking |
| `PlayerAwards` | `player_id` | Awards history |
| `PlayerCompare` | `player_id_list`, `vs_player_id_list` | Head-to-head compare |
| `PlayerEstimatedMetrics` | `season` | Estimated advanced metrics |
| `PlayerFantasyProfileBarGraph` | `player_id`, `season` | Fantasy stats |
| `PlayerGameStreakFinder` | `player_id` | Game streak finder |
| `PlayerIndex` | `season` | Player index listing |
| `PlayerNextNGames` | `player_id` | Upcoming games |
| `PlayerVsPlayer` | `player_id`, `vs_player_id` | Player vs player |
| `PlayerCareerByCollege` | `college` | Players by college |
| `PlayerCareerByCollegeRollup` | — | College rollup |
| `CommonAllPlayers` | `season` | All players for season |

**Team Stats:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `CommonTeamRoster` | `team_id`, `season` | Roster with height/weight/position |
| `TeamGameLog` | `team_id`, `season` | Team game-by-game |
| `TeamGameLogs` | `team_id`, `season` | Alternate team game logs |
| `TeamDashboardByGeneralSplits` | `team_id`, `season` | Team stats by split |
| `TeamDashboardByShootingSplits` | `team_id`, `season` | Team shooting splits |
| `TeamDashLineups` | `team_id`, `season` | Lineup combinations |
| `TeamDashPtPass` | `team_id`, `season` | Team passing tracking |
| `TeamDashPtReb` | `team_id`, `season` | Team rebounding tracking |
| `TeamDashPtShots` | `team_id`, `season` | Team shot tracking |
| `TeamDetails` | `team_id` | Team info and history |
| `TeamEstimatedMetrics` | `season` | Team estimated metrics |
| `TeamHistoricalLeaders` | `team_id` | All-time team leaders |
| `TeamInfoCommon` | `team_id` | Common team info |
| `TeamPlayerDashboard` | `team_id`, `season` | Player dashboard for team |
| `TeamPlayerOnOffDetails` | `team_id`, `season` | On/off court details |
| `TeamPlayerOnOffSummary` | `team_id`, `season` | On/off court summary |
| `TeamVsPlayer` | `team_id`, `vs_player_id` | Team vs player |
| `TeamYearByYearStats` | `team_id` | Year-by-year history |
| `TeamGameStreakFinder` | `team_id` | Team streak finder |
| `TeamAndPlayersVsPlayers` | `team_id` | Team + players vs players |

**League / Standings:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `LeagueStandings` | `season`, `league_id` | League standings |
| `LeagueStandingsV3` | `season`, `league_id` | V3 standings (RECOMMENDED) |
| `LeagueLeaders` | `season`, `stat_category` | Stat leaders |
| `LeagueGameFinder` | various filters | Search games with complex filters |
| `LeagueGameLog` | `season` | All games in a season |
| `LeagueDashPlayerStats` | `season` | All player stats |
| `LeagueDashTeamStats` | `season` | All team stats |
| `LeagueDashLineups` | `season` | League lineup data |
| `LeagueDashPlayerClutch` | `season` | Clutch player stats |
| `LeagueDashTeamClutch` | `season` | Clutch team stats |
| `LeagueDashPlayerBioStats` | `season` | Bio/physical stats |
| `LeagueDashPlayerShotLocations` | `season` | Shot location data |
| `LeagueDashTeamShotLocations` | `season` | Team shot locations |
| `LeagueDashPlayerPtShot` | `season` | Player shot tracking |
| `LeagueDashTeamPtShot` | `season` | Team shot tracking |
| `LeagueDashOppPtShot` | `season` | Opponent shot tracking |
| `LeagueDashPtStats` | `season` | Tracking stats |
| `LeagueDashPtDefend` | `season` | Defensive tracking |
| `LeagueDashPtTeamDefend` | `season` | Team defensive tracking |
| `LeagueHustleStatsPlayer` | `season` | Hustle stats (players) |
| `LeagueHustleStatsTeam` | `season` | Hustle stats (teams) |
| `LeagueLineupViz` | `season` | Lineup visualization |
| `LeaguePlayerOnDetails` | `season` | On-court details |
| `LeagueSeasonMatchups` | `season` | Matchup data |
| `ISTStandings` | `season` | In-Season Tournament standings |
| `PlayoffPicture` | `season` | Playoff race |

**Box Score Endpoints (multiple versions):**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `BoxScoreTraditionalV2` / `V3` | `game_id` | Standard box score |
| `BoxScoreAdvancedV2` / `V3` | `game_id` | Advanced stats (OffRtg, DefRtg, etc.) |
| `BoxScoreMiscV2` / `V3` | `game_id` | Miscellaneous stats |
| `BoxScoreFourFactorsV2` / `V3` | `game_id` | Four Factors analysis |
| `BoxScoreScoringV2` / `V3` | `game_id` | Scoring breakdown |
| `BoxScoreUsageV2` / `V3` | `game_id` | Usage rates |
| `BoxScoreDefensiveV2` | `game_id` | Defensive stats |
| `BoxScoreHustleV2` | `game_id` | Hustle stats |
| `BoxScoreMatchupsV3` | `game_id` | Matchup data |
| `BoxScorePlayerTrackV3` | `game_id` | Player tracking data |
| `BoxScoreSummaryV2` / `V3` | `game_id` | Game summary |
| `HustleStatsBoxScore` | `game_id` | Hustle box score |

**Play-by-Play:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `PlayByPlayV3` | `game_id` | Play-by-play events (RECOMMENDED) |
| `PlayByPlayV2` | `game_id` | Legacy PBP (DEPRECATED — returns empty) |
| `PlayByPlay` | `game_id` | Oldest version |

**Shot Charts:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `ShotChartDetail` | `player_id`, `team_id`, `game_id`, `season` | Shot-level data with x/y coordinates |
| `ShotChartLeagueWide` | `season` | League-wide shot distribution |
| `ShotChartLineupDetail` | `group_id`, `season` | Lineup shot data |

**Draft:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `DraftHistory` | `season` | Draft picks |
| `DraftBoard` | `season` | Draft board |
| `DraftCombineStats` | `season` | Combine stats |
| `DraftCombinePlayerAnthro` | `season` | Physical measurements |
| `DraftCombineDrillResults` | `season` | Drill results |
| `DraftCombineSpotShooting` | `season` | Spot shooting |
| `DraftCombineNonStationaryShooting` | `season` | Moving shooting |

**Advanced & Specialty:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `SynergyPlayTypes` | `season` | Play type analysis |
| `WinProbabilityPBP` | `game_id` | Win probability per play |
| `GameRotation` | `game_id` | Rotation/substitution data |
| `MatchupsRollup` | `season` | Matchup statistics |
| `AllTimeLeadersGrids` | — | All-time stat leaders |
| `AssistLeaders` | `season` | Assist leaders |
| `AssistTracker` | `season` | Assist tracking |
| `DunkScoreLeaders` | `season` | Dunk score leaders |
| `GravityLeaders` | `season` | Gravity metric leaders |
| `FranchiseHistory` | — | Franchise history |
| `FranchiseLeaders` | `team_id` | Franchise stat leaders |
| `FranchisePlayers` | `team_id` | Franchise players |
| `FantasyWidget` | `season` | Fantasy data |
| `CumeStatsPlayer` | `player_id`, `game_ids` | Cumulative player stats |
| `CumeStatsTeam` | `team_id`, `game_ids` | Cumulative team stats |
| `DefenseHub` | `season` | Defensive hub stats |
| `HomepageLeaders` | `season` | Homepage leader data |
| `HomepageV2` | `season` | Homepage data |
| `LeadersTiles` | `season` | Leader tiles |
| `InfographicFanDuelPlayer` | `game_id` | FanDuel infographic |

**Video:**
| Endpoint Class | Key Parameters | Description |
|---|---|---|
| `VideoDetails` | `game_id`, `player_id` | Video clip metadata |
| `VideoDetailsAsset` | `game_id` | Video asset URLs |
| `VideoEvents` | `game_id` | Video event markers |
| `VideoEventsAsset` | `game_id` | Video event assets |
| `VideoStatus` | `game_date` | Video availability |

---

### 4.3 Static Data — Offline Team & Player Lookups

No network calls required. Data is bundled in the package.

#### Teams

```python
# src/nba_api/stats/static/teams.py

from nba_api.stats.static import teams

# All 30 NBA teams
teams.get_teams()
# Returns: [{"id": 1610612738, "full_name": "Boston Celtics", "abbreviation": "BOS",
#            "nickname": "Celtics", "city": "Boston", "state": "Massachusetts",
#            "year_founded": 1946}, ...]

# Lookup functions (all accept regex patterns unless noted)
teams.find_team_by_abbreviation("BOS")         # exact match -> single dict or None
teams.find_team_name_by_id(1610612738)          # exact match -> single dict or None
teams.find_teams_by_full_name("Celtics")        # regex -> list of dicts
teams.find_teams_by_city("Boston")              # regex -> list of dicts
teams.find_teams_by_nickname("Celtics")         # regex -> list of dicts
teams.find_teams_by_state("Massachusetts")      # regex -> list of dicts
teams.find_teams_by_year_founded(1946)          # exact year -> list of dicts
teams.find_teams_by_championship_year(2024)     # year -> team full_name string

# WNBA equivalents
teams.get_wnba_teams()
teams.find_wnba_team_by_abbreviation("LVA")
# ... all the same functions with wnba_ prefix
```

**Team dict structure:**
```python
{
    "id": 1610612738,           # NBA team ID (used in all API calls)
    "full_name": "Boston Celtics",
    "abbreviation": "BOS",     # 3-letter tricode
    "nickname": "Celtics",
    "city": "Boston",
    "state": "Massachusetts",
    "year_founded": 1946
}
```

#### Players

```python
# src/nba_api/stats/static/players.py

from nba_api.stats.static import players

# All players (active + inactive)
players.get_players()
players.get_active_players()
players.get_inactive_players()

# Lookup functions (all accept regex patterns unless noted)
players.find_player_by_id(203999)                # exact match -> single dict or None
players.find_players_by_full_name("LeBron")      # regex -> list of dicts
players.find_players_by_first_name("LeBron")     # regex -> list of dicts
players.find_players_by_last_name("James")       # regex -> list of dicts

# WNBA equivalents
players.get_wnba_players()
players.get_wnba_active_players()
players.find_wnba_player_by_id(100001)
# ... all the same functions with wnba_ prefix
```

**Player dict structure:**
```python
{
    "id": 203999,              # NBA person ID (used in all API calls)
    "full_name": "Nikola Jokic",
    "first_name": "Nikola",
    "last_name": "Jokic",
    "is_active": True
}
```

Note: Player name lookups automatically strip accents (e.g., searching "Jokic" matches "Jokić").

---

## 5. Data Format Details

### 5.1 Stats API — V2 Legacy Format (tabular)

V2 endpoints return data as `resultSets` containing `headers` + `rowSet`:

```json
{
    "resource": "leaguegamefinder",
    "parameters": {"Season": "2025-26", ...},
    "resultSets": [
        {
            "name": "LeagueGameFinderResults",
            "headers": ["SEASON_ID", "TEAM_ID", "GAME_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", ...],
            "rowSet": [
                ["22025", 1610612747, "0022501001", "2026-01-15", "LAL @ DEN", "L", 108, ...],
                ...
            ]
        }
    ]
}
```

Use `get_normalized_dict()` to convert to list-of-dicts, or `dataset.get_data_frame()` for pandas.

### 5.2 Stats API — V3 Format (nested JSON)

V3 endpoints return nested JSON that the library parses via custom parsers in `src/nba_api/stats/endpoints/_parsers/`. The parsed output is presented through the same `DataSet` interface.

### 5.3 Live API Format (nested JSON)

Live endpoints return nested JSON directly. Access via `.get_dict()` or `.get_json()`.

### 5.4 Output Methods (available on all endpoints)

| Method | Returns | Notes |
|---|---|---|
| `endpoint.get_dict()` | `dict` | Raw API response |
| `endpoint.get_json()` | `str` | JSON string |
| `endpoint.get_response()` | `str` | Raw HTTP response text |
| `endpoint.get_normalized_dict()` | `dict` | Normalized (V2 stats only) |
| `endpoint.get_data_frames()` | `list[DataFrame]` | All datasets as DataFrames |
| `dataset.get_dict()` | `dict` or `list` | Single dataset |
| `dataset.get_json()` | `str` | Single dataset as JSON |
| `dataset.get_data_frame()` | `DataFrame` | Single dataset (requires pandas) |

---

## 6. Rate Limits & Throttling

**No built-in rate limiting.** The library has no `time.sleep()`, request queuing, or throttle mechanisms.

**NBA.com server-side behavior (undocumented):**
- The APIs are public and generally permissive
- Aggressive polling (e.g., multiple requests per second sustained) may result in temporary blocks (HTTP 403/429)
- Requests without proper browser-like headers will be blocked

**Recommendations for integration:**
1. Add 1-second minimum delay between requests
2. Implement exponential backoff on HTTP errors
3. Cache responses (live scoreboard updates every ~15 seconds during games)
4. Use the built-in session pooling (`requests.Session` is reused automatically)
5. Pass a `proxy` (string or list for rotation) for high-volume usage

**Proxy support:**
```python
# Single proxy
ScoreBoard(proxy="http://proxy.example.com:8080")

# Proxy rotation (randomly selected per request)
ScoreBoard(proxy=["http://proxy1:8080", "http://proxy2:8080", "http://proxy3:8080"])
```

---

## 7. Code Snippets — Common Integration Patterns

### Get today's live scoreboard

```python
from nba_api.live.nba.endpoints import ScoreBoard

scoreboard = ScoreBoard()
games = scoreboard.games.get_dict()

for game in games:
    home = game["homeTeam"]
    away = game["awayTeam"]
    print(f"{away['teamCity']} {away['teamName']} ({away['score']}) "
          f"@ {home['teamCity']} {home['teamName']} ({home['score']})")
    print(f"  Status: {game['gameStatusText']} | Period: {game['period']} | Clock: {game['gameClock']}")
    print(f"  Game ID: {game['gameId']}")
```

### Check if a game is live, upcoming, or final

```python
from nba_api.live.nba.endpoints import ScoreBoard

scoreboard = ScoreBoard()

for game in scoreboard.games.get_dict():
    status = game["gameStatus"]
    if status == 1:
        print(f"UPCOMING: {game['gameStatusText']}")
    elif status == 2:
        print(f"LIVE: Q{game['period']} {game['gameClock']}")
    elif status == 3:
        print(f"FINAL: {game['homeTeam']['score']}-{game['awayTeam']['score']}")
```

### Parse the game clock

```python
import re

def parse_game_clock(clock_str):
    """Parse ISO 8601 duration 'PT05M22.00S' -> (minutes, seconds)"""
    if not clock_str:
        return (0, 0.0)
    match = re.match(r'PT(\d+)M([\d.]+)S', clock_str)
    if match:
        return (int(match.group(1)), float(match.group(2)))
    return (0, 0.0)

# Usage:
minutes, seconds = parse_game_clock("PT05M22.00S")  # -> (5, 22.0)
```

### Get a specific date's scoreboard (Stats API)

```python
from nba_api.stats.endpoints import ScoreboardV3

scoreboard = ScoreboardV3(game_date="2026-02-07")

# Game headers as DataFrame
games_df = scoreboard.game_header.get_data_frame()
# Columns: gameId, gameCode, gameStatus, gameStatusText, period, gameClock, gameTimeUTC, ...

# Line scores as DataFrame
scores_df = scoreboard.line_score.get_data_frame()
# Columns: gameId, teamId, teamCity, teamName, teamTricode, wins, losses, score, ...
```

### Look up a team and get their game log

```python
from nba_api.stats.static import teams
from nba_api.stats.endpoints import TeamGameLog

# Find team
celtics = teams.find_team_by_abbreviation("BOS")
team_id = celtics["id"]  # 1610612738

# Get season game log
game_log = TeamGameLog(team_id=team_id, season="2025-26")
df = game_log.team_game_log.get_data_frame()
# Columns: Team_ID, Game_ID, GAME_DATE, MATCHUP, WL, W, L, W_PCT, MIN, FGM, FGA, ...
```

### Look up a player and get career stats

```python
from nba_api.stats.static import players
from nba_api.stats.endpoints import PlayerCareerStats

# Find player
jokic = players.find_players_by_full_name("Nikola Jokic")[0]
player_id = jokic["id"]  # 203999

# Get career stats
career = PlayerCareerStats(player_id=player_id)
df = career.season_totals_regular_season.get_data_frame()
# Columns: PLAYER_ID, SEASON_ID, LEAGUE_ID, TEAM_ID, GP, GS, MIN, FGM, FGA, ...
```

### Get live box score for a specific game

```python
from nba_api.live.nba.endpoints import BoxScore

box = BoxScore(game_id="0022500780")

# Game status
details = box.game_details.get_dict()
print(f"Status: {details['gameStatusText']}, Period: {details['period']}")

# Team scores
home = box.home_team_stats.get_dict()
away = box.away_team_stats.get_dict()
print(f"{home['teamName']}: {home['score']}  {away['teamName']}: {away['score']}")

# Player stats
for player in box.home_team_player_stats.get_dict():
    stats = player["statistics"]
    print(f"  {player['name']}: {stats['points']}pts {stats['reboundsTotal']}reb {stats['assists']}ast")
```

### Determine halftime

```python
# The API does not have a dedicated "halftime" status code.
# Halftime is indicated by gameStatus=2 with gameStatusText containing "Half"
# or by period=2 with gameClock="PT00M00.00S"

def is_halftime(game):
    """Check if game is at halftime."""
    if game["gameStatus"] != 2:
        return False
    status_text = game.get("gameStatusText", "")
    if "Half" in status_text:
        return True
    # Also check: period 2 ended, period 3 not started
    if game["period"] == 2 and game["gameClock"] == "PT00M00.00S":
        return True
    return False
```

---

## 8. NBA Team IDs Reference

All 30 NBA teams and their IDs (used across all endpoints):

| ID | Abbreviation | Team |
|---|---|---|
| 1610612737 | ATL | Atlanta Hawks |
| 1610612738 | BOS | Boston Celtics |
| 1610612751 | BKN | Brooklyn Nets |
| 1610612766 | CHA | Charlotte Hornets |
| 1610612741 | CHI | Chicago Bulls |
| 1610612739 | CLE | Cleveland Cavaliers |
| 1610612742 | DAL | Dallas Mavericks |
| 1610612743 | DEN | Denver Nuggets |
| 1610612765 | DET | Detroit Pistons |
| 1610612744 | GSW | Golden State Warriors |
| 1610612745 | HOU | Houston Rockets |
| 1610612754 | IND | Indiana Pacers |
| 1610612746 | LAC | LA Clippers |
| 1610612747 | LAL | Los Angeles Lakers |
| 1610612763 | MEM | Memphis Grizzlies |
| 1610612748 | MIA | Miami Heat |
| 1610612749 | MIL | Milwaukee Bucks |
| 1610612750 | MIN | Minnesota Timberwolves |
| 1610612740 | NOP | New Orleans Pelicans |
| 1610612752 | NYK | New York Knicks |
| 1610612760 | OKC | Oklahoma City Thunder |
| 1610612753 | ORL | Orlando Magic |
| 1610612755 | PHI | Philadelphia 76ers |
| 1610612756 | PHX | Phoenix Suns |
| 1610612757 | POR | Portland Trail Blazers |
| 1610612758 | SAC | Sacramento Kings |
| 1610612759 | SAS | San Antonio Spurs |
| 1610612761 | TOR | Toronto Raptors |
| 1610612762 | UTA | Utah Jazz |
| 1610612764 | WAS | Washington Wizards |

---

## 9. Known Issues & Deprecations

| Issue | Details | Workaround |
|---|---|---|
| `ScoreboardV2` broken | Line score data broken for 2025-26 season | Use `ScoreboardV3` |
| `PlayByPlayV2` empty | Returns empty JSON | Use `PlayByPlayV3` or live `PlayByPlay` |
| `LeagueGameFinder` `game_id_nullable` | Parameter silently ignored by NBA.com | Filter results client-side |
| `TeamDashboardByGeneralSplits` plus/minus | `plus_minus='Y'` returns incorrect values | Use `plus_minus='N'` (default) |
| Static data staleness | Player/team data updated manually per release | Check package version for latest data |

---

## 10. Game ID Format

NBA game IDs follow this pattern: `00XYYZZZZ`

| Segment | Meaning |
|---|---|
| `00` | League (`00` = NBA, `10` = WNBA, `20` = G-League) |
| `X` | Season type (`1` = preseason, `2` = regular, `3` = all-star, `4` = playoffs) |
| `YY` | Season year suffix (e.g., `25` for 2025-26) |
| `ZZZZ` | Sequential game number |

Example: `0022500180` = NBA (`00`), regular season (`2`), 2025-26 (`25`), game #180 (`00180`).

---

## 11. Season Format

Season strings use the format `"YYYY-YY"`: e.g., `"2025-26"`.

The library tracks the current season in `nba_api.stats.library.parameters.Season`:
```python
from nba_api.stats.library.parameters import Season
print(Season.current_season)  # "2025-26"
print(Season.default)         # "2025-26"
```

---

## 12. HTTP Internals

The HTTP layer is implemented in `src/nba_api/library/http.py`:

```python
class NBAHTTP:
    _session = None  # Class-level persistent session

    @classmethod
    def get_session(cls):
        """Returns a reusable requests.Session for connection pooling."""
        if cls._session is None:
            cls._session = requests.Session()
        return cls._session

    @classmethod
    def set_session(cls, session):
        """Replace the session (useful for testing or custom config)."""
        cls._session = session

    def send_api_request(self, endpoint, parameters, referer=None,
                         proxy=None, headers=None, timeout=None,
                         raise_exception_on_error=False):
        # Sorts parameters alphabetically (required by some NBA endpoints)
        # Supports proxy rotation from a list
        # Returns NBAResponse object
        ...
```

Two subclasses:
- `NBAStatsHTTP` (`src/nba_api/stats/library/http.py`) — targets `stats.nba.com`
- `NBALiveHTTP` (`src/nba_api/live/nba/library/http.py`) — targets `cdn.nba.com`

Both override `clean_contents()` to handle NBA.com error responses.

**Custom session injection (for testing or middleware):**
```python
import requests
from nba_api.library.http import NBAHTTP

# Inject a custom session with retry logic
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount("https://", adapter)
NBAHTTP.set_session(session)
```
