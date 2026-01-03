"""
HELIOS NBA API Bridge

Core integration layer between HELIOS and NBA.com APIs.
Provides automated data fetching with caching, rate limiting,
and HELIOS-specific data transformations.

Usage:
    from helios.nba_api_bridge import NBAAPIBridge

    bridge = NBAAPIBridge()

    # Automated grading
    actuals = bridge.get_player_actuals(game_id='0022400456', player_name='Andrew Nembhard')

    # 3PA analysis
    stats = bridge.get_player_3pa_stats(player_id=1631115, last_n_games=20)

    # Minutes analysis
    minutes = bridge.get_player_minutes_stats(player_id=1631115, last_n_games=20)
"""

import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, asdict
import numpy as np

# NBA API imports
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import (
    playergamelog,
    boxscoretraditionalv3,
    boxscoresummaryv2,
    leaguegamefinder,
    playbyplayv3,
    commonplayerinfo,
)
from nba_api.live.nba.endpoints import scoreboard, odds


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_CACHE_DIR = Path(__file__).parent / '.cache'
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour for most data
BOXSCORE_CACHE_TTL_SECONDS = 86400 * 7  # 7 days for completed game boxscores
REQUEST_DELAY_SECONDS = 0.6  # Rate limit protection


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class PlayerActuals:
    """Actual statistics for a player in a specific game."""
    player_id: int
    player_name: str
    game_id: str
    game_date: str
    team_id: int
    team_tricode: str
    minutes: float
    points: int
    rebounds: int
    assists: int
    steals: int
    blocks: int
    turnovers: int
    fg_made: int
    fg_attempted: int
    fg3_made: int
    fg3_attempted: int
    ft_made: int
    ft_attempted: int
    plus_minus: int

    def get_stat(self, prop_type: str) -> Union[int, float]:
        """Get stat value by prop type abbreviation."""
        mapping = {
            'PTS': self.points,
            'REB': self.rebounds,
            'AST': self.assists,
            'STL': self.steals,
            'BLK': self.blocks,
            'TOV': self.turnovers,
            '3PM': self.fg3_made,
            '3PA': self.fg3_attempted,
            'FGM': self.fg_made,
            'FGA': self.fg_attempted,
            'FTM': self.ft_made,
            'FTA': self.ft_attempted,
            'MIN': self.minutes,
            'PRA': self.points + self.rebounds + self.assists,
            'PR': self.points + self.rebounds,
            'PA': self.points + self.assists,
            'RA': self.rebounds + self.assists,
            'BLST': self.blocks + self.steals,
        }
        return mapping.get(prop_type.upper(), None)


@dataclass
class ThreePointAnalysis:
    """3-point attempt analysis for a player."""
    player_id: int
    player_name: str
    games_analyzed: int
    total_3pa: int
    avg_3pa: float
    std_3pa: float
    cov_3pa: float  # Coefficient of variation
    min_3pa: int
    max_3pa: int
    games_under_5_3pa: int
    pct_games_under_5_3pa: float
    last_10_avg: float
    trend: str  # 'up', 'down', 'stable'
    stability_grade: str  # 'A', 'B', 'C', 'D', 'F'


@dataclass
class MinutesAnalysis:
    """Minutes volatility analysis for a player."""
    player_id: int
    player_name: str
    games_analyzed: int
    avg_minutes: float
    std_minutes: float
    cov_minutes: float
    min_minutes: float
    max_minutes: float
    games_under_20_min: int
    pct_games_under_20_min: float
    last_5_avg: float
    volatility_grade: str  # 'LOW', 'MEDIUM', 'HIGH'


@dataclass
class GradingResult:
    """Result of grading a single pick against actuals."""
    player_name: str
    prop_type: str
    line: float
    pick_direction: str  # 'O' or 'U'
    actual: Union[int, float]
    result: str  # 'W', 'L', 'P' (push)
    margin: float
    game_id: str
    game_date: str


# ============================================================================
# CACHE UTILITIES
# ============================================================================

class SimpleCache:
    """Simple file-based cache for API responses."""

    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate cache key from endpoint and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_input = f"{endpoint}:{param_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"

    def get(self, endpoint: str, params: Dict, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> Optional[Dict]:
        """Get cached response if valid."""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=ttl_seconds):
                return None

            return cached['data']
        except (json.JSONDecodeError, KeyError):
            return None

    def set(self, endpoint: str, params: Dict, data: Dict) -> None:
        """Cache a response."""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)

        cached = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'params': params,
            'data': data
        }

        with open(cache_path, 'w') as f:
            json.dump(cached, f)

    def clear(self) -> int:
        """Clear all cached data. Returns count of files removed."""
        count = 0
        for cache_file in self.cache_dir.glob('*.json'):
            cache_file.unlink()
            count += 1
        return count


# ============================================================================
# MAIN BRIDGE CLASS
# ============================================================================

class NBAAPIBridge:
    """
    HELIOS integration bridge for NBA API.

    Provides:
    - Automated boxscore fetching and grading
    - Player game log analysis (3PA, minutes)
    - Caching to respect rate limits
    - Player/team lookup utilities
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        request_delay: float = REQUEST_DELAY_SECONDS,
        use_cache: bool = True
    ):
        self.cache = SimpleCache(cache_dir or DEFAULT_CACHE_DIR) if use_cache else None
        self.request_delay = request_delay
        self._last_request_time = 0

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    # ========================================================================
    # PLAYER/TEAM LOOKUP
    # ========================================================================

    def find_player(self, name: str) -> Optional[Dict]:
        """Find player by name (partial match supported)."""
        results = players.find_players_by_full_name(name)
        if results:
            return results[0]
        # Try last name only
        results = players.find_players_by_last_name(name)
        if results:
            return results[0]
        return None

    def find_player_id(self, name: str) -> Optional[int]:
        """Get player ID by name."""
        player = self.find_player(name)
        return player['id'] if player else None

    def find_team(self, identifier: str) -> Optional[Dict]:
        """Find team by name, city, or abbreviation."""
        # Try abbreviation first
        results = teams.find_teams_by_abbreviation(identifier)
        if results:
            return results[0]
        # Try city
        results = teams.find_teams_by_city(identifier)
        if results:
            return results[0]
        # Try full name
        results = teams.find_teams_by_full_name(identifier)
        if results:
            return results[0]
        return None

    def get_active_players(self) -> List[Dict]:
        """Get all active NBA players."""
        return players.get_active_players()

    # ========================================================================
    # BOXSCORE / GRADING
    # ========================================================================

    def get_boxscore(self, game_id: str) -> Dict[str, Any]:
        """
        Fetch complete boxscore for a game.

        Returns dict with 'players' list containing PlayerActuals-compatible data.
        """
        cache_key_params = {'game_id': game_id}

        if self.cache:
            cached = self.cache.get('boxscore', cache_key_params, BOXSCORE_CACHE_TTL_SECONDS)
            if cached:
                return cached

        self._rate_limit()

        try:
            box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
            player_stats = box.player_stats.get_dict()

            result = {
                'game_id': game_id,
                'players': []
            }

            for player in player_stats:
                result['players'].append({
                    'player_id': player.get('personId'),
                    'player_name': f"{player.get('firstName', '')} {player.get('familyName', '')}".strip(),
                    'team_id': player.get('teamId'),
                    'team_tricode': player.get('teamTricode'),
                    'minutes': self._parse_minutes(player.get('minutes', 'PT0M')),
                    'points': player.get('points', 0) or 0,
                    'rebounds': player.get('reboundsTotal', 0) or 0,
                    'assists': player.get('assists', 0) or 0,
                    'steals': player.get('steals', 0) or 0,
                    'blocks': player.get('blocks', 0) or 0,
                    'turnovers': player.get('turnovers', 0) or 0,
                    'fg_made': player.get('fieldGoalsMade', 0) or 0,
                    'fg_attempted': player.get('fieldGoalsAttempted', 0) or 0,
                    'fg3_made': player.get('threePointersMade', 0) or 0,
                    'fg3_attempted': player.get('threePointersAttempted', 0) or 0,
                    'ft_made': player.get('freeThrowsMade', 0) or 0,
                    'ft_attempted': player.get('freeThrowsAttempted', 0) or 0,
                    'plus_minus': player.get('plusMinusPoints', 0) or 0,
                })

            if self.cache:
                self.cache.set('boxscore', cache_key_params, result)

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to fetch boxscore for game {game_id}: {e}")

    def _parse_minutes(self, minutes_str: str) -> float:
        """Parse minutes from various formats (PT32M15S, '32:15', 32, etc.)."""
        if minutes_str is None:
            return 0.0

        if isinstance(minutes_str, (int, float)):
            return float(minutes_str)

        minutes_str = str(minutes_str).strip()

        # ISO 8601 duration format: PT32M15.00S
        if minutes_str.startswith('PT'):
            try:
                minutes_str = minutes_str[2:]  # Remove PT
                minutes = 0.0
                if 'M' in minutes_str:
                    m_part, rest = minutes_str.split('M')
                    minutes += float(m_part)
                    minutes_str = rest
                if 'S' in minutes_str:
                    s_part = minutes_str.replace('S', '')
                    if s_part:
                        minutes += float(s_part) / 60
                return round(minutes, 1)
            except:
                return 0.0

        # MM:SS format
        if ':' in minutes_str:
            try:
                parts = minutes_str.split(':')
                return round(float(parts[0]) + float(parts[1]) / 60, 1)
            except:
                return 0.0

        # Plain number
        try:
            return float(minutes_str)
        except:
            return 0.0

    def get_player_actuals(
        self,
        game_id: str,
        player_name: Optional[str] = None,
        player_id: Optional[int] = None
    ) -> Optional[PlayerActuals]:
        """
        Get actual statistics for a specific player in a game.

        Args:
            game_id: NBA game ID (e.g., '0022400456')
            player_name: Player name (partial match)
            player_id: Player ID (takes precedence over name)

        Returns:
            PlayerActuals dataclass or None if player not found
        """
        boxscore = self.get_boxscore(game_id)

        for player in boxscore['players']:
            # Match by ID
            if player_id and player['player_id'] == player_id:
                return PlayerActuals(
                    game_id=game_id,
                    game_date='',  # Would need separate call to get date
                    **player
                )

            # Match by name (case-insensitive partial match)
            if player_name:
                player_name_lower = player_name.lower()
                box_name_lower = player['player_name'].lower()
                if player_name_lower in box_name_lower or box_name_lower in player_name_lower:
                    return PlayerActuals(
                        game_id=game_id,
                        game_date='',
                        **player
                    )

        return None

    def grade_pick(
        self,
        game_id: str,
        player_name: str,
        prop_type: str,
        line: float,
        pick_direction: str
    ) -> Optional[GradingResult]:
        """
        Grade a single pick against actual boxscore data.

        Args:
            game_id: NBA game ID
            player_name: Player name
            prop_type: Prop type (PTS, REB, AST, 3PM, etc.)
            line: The betting line
            pick_direction: 'O' for over, 'U' for under

        Returns:
            GradingResult or None if player not found
        """
        actuals = self.get_player_actuals(game_id, player_name=player_name)

        if not actuals:
            return None

        actual_value = actuals.get_stat(prop_type)
        if actual_value is None:
            return None

        # Determine result
        pick_direction = pick_direction.upper()
        if actual_value > line:
            result = 'W' if pick_direction == 'O' else 'L'
        elif actual_value < line:
            result = 'W' if pick_direction == 'U' else 'L'
        else:
            result = 'P'  # Push

        # Calculate margin (positive = favorable)
        if pick_direction == 'O':
            margin = actual_value - line
        else:
            margin = line - actual_value

        return GradingResult(
            player_name=actuals.player_name,
            prop_type=prop_type,
            line=line,
            pick_direction=pick_direction,
            actual=actual_value,
            result=result,
            margin=margin,
            game_id=game_id,
            game_date=actuals.game_date
        )

    def grade_picks_batch(
        self,
        picks: List[Dict]
    ) -> List[GradingResult]:
        """
        Grade multiple picks.

        Args:
            picks: List of dicts with keys: game_id, player_name, prop_type, line, pick_direction

        Returns:
            List of GradingResult objects
        """
        results = []
        for pick in picks:
            result = self.grade_pick(
                game_id=pick['game_id'],
                player_name=pick['player_name'],
                prop_type=pick['prop_type'],
                line=pick['line'],
                pick_direction=pick['pick_direction']
            )
            if result:
                results.append(result)
        return results

    # ========================================================================
    # PLAYER GAME LOG ANALYSIS
    # ========================================================================

    def get_player_game_logs(
        self,
        player_id: int,
        season: str = '2024-25',
        season_type: str = 'Regular Season'
    ) -> List[Dict]:
        """
        Fetch player game logs for a season.

        Returns list of game log entries with stats.
        """
        cache_key_params = {
            'player_id': player_id,
            'season': season,
            'season_type': season_type
        }

        if self.cache:
            cached = self.cache.get('player_game_log', cache_key_params)
            if cached:
                return cached

        self._rate_limit()

        try:
            logs = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star=season_type
            )
            df = logs.player_game_log.get_dict()

            # Convert to list of dicts with standardized keys
            games = []
            headers = df.get('headers', [])
            for row in df.get('data', []):
                game = dict(zip(headers, row))
                games.append(game)

            if self.cache:
                self.cache.set('player_game_log', cache_key_params, games)

            return games

        except Exception as e:
            raise RuntimeError(f"Failed to fetch game logs for player {player_id}: {e}")

    def get_player_3pa_stats(
        self,
        player_id: int,
        last_n_games: int = 20,
        season: str = '2024-25'
    ) -> ThreePointAnalysis:
        """
        Analyze 3-point attempt patterns for a player.

        Returns ThreePointAnalysis with stability metrics.
        """
        games = self.get_player_game_logs(player_id, season)

        if not games:
            raise ValueError(f"No game logs found for player {player_id}")

        # Get player name from first game
        player_name = games[0].get('MATCHUP', '').split()[0] if games else 'Unknown'

        # Limit to last N games
        games = games[:last_n_games]

        # Extract 3PA values
        three_pa_values = [g.get('FG3A', 0) or 0 for g in games]

        if not three_pa_values:
            raise ValueError(f"No 3PA data found for player {player_id}")

        arr = np.array(three_pa_values)
        avg = float(np.mean(arr))
        std = float(np.std(arr))
        cov = std / avg if avg > 0 else 0

        # Last 10 for trend
        last_10 = arr[:10] if len(arr) >= 10 else arr
        last_10_avg = float(np.mean(last_10))

        # Trend determination
        if len(arr) >= 10:
            first_half = np.mean(arr[len(arr)//2:])
            second_half = np.mean(arr[:len(arr)//2])
            if second_half > first_half * 1.1:
                trend = 'up'
            elif second_half < first_half * 0.9:
                trend = 'down'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        # Stability grade based on CoV
        if cov < 0.2:
            grade = 'A'
        elif cov < 0.35:
            grade = 'B'
        elif cov < 0.5:
            grade = 'C'
        elif cov < 0.7:
            grade = 'D'
        else:
            grade = 'F'

        # Games under 5 3PA (floor concern)
        games_under_5 = int(np.sum(arr < 5))

        return ThreePointAnalysis(
            player_id=player_id,
            player_name=player_name,
            games_analyzed=len(games),
            total_3pa=int(np.sum(arr)),
            avg_3pa=round(avg, 2),
            std_3pa=round(std, 2),
            cov_3pa=round(cov, 3),
            min_3pa=int(np.min(arr)),
            max_3pa=int(np.max(arr)),
            games_under_5_3pa=games_under_5,
            pct_games_under_5_3pa=round(games_under_5 / len(arr) * 100, 1),
            last_10_avg=round(last_10_avg, 2),
            trend=trend,
            stability_grade=grade
        )

    def get_player_minutes_stats(
        self,
        player_id: int,
        last_n_games: int = 20,
        season: str = '2024-25'
    ) -> MinutesAnalysis:
        """
        Analyze minutes volatility for a player.

        Returns MinutesAnalysis with volatility metrics.
        """
        games = self.get_player_game_logs(player_id, season)

        if not games:
            raise ValueError(f"No game logs found for player {player_id}")

        player_name = games[0].get('MATCHUP', '').split()[0] if games else 'Unknown'

        # Limit to last N games
        games = games[:last_n_games]

        # Extract minutes values
        minutes_values = [self._parse_minutes(g.get('MIN', 0)) for g in games]

        if not minutes_values:
            raise ValueError(f"No minutes data found for player {player_id}")

        arr = np.array(minutes_values)
        avg = float(np.mean(arr))
        std = float(np.std(arr))
        cov = std / avg if avg > 0 else 0

        # Last 5 for recent form
        last_5 = arr[:5] if len(arr) >= 5 else arr
        last_5_avg = float(np.mean(last_5))

        # Volatility grade
        if cov < 0.1:
            grade = 'LOW'
        elif cov < 0.2:
            grade = 'MEDIUM'
        else:
            grade = 'HIGH'

        # Games under 20 minutes (role risk)
        games_under_20 = int(np.sum(arr < 20))

        return MinutesAnalysis(
            player_id=player_id,
            player_name=player_name,
            games_analyzed=len(games),
            avg_minutes=round(avg, 1),
            std_minutes=round(std, 2),
            cov_minutes=round(cov, 3),
            min_minutes=round(float(np.min(arr)), 1),
            max_minutes=round(float(np.max(arr)), 1),
            games_under_20_min=games_under_20,
            pct_games_under_20_min=round(games_under_20 / len(arr) * 100, 1),
            last_5_avg=round(last_5_avg, 1),
            volatility_grade=grade
        )

    # ========================================================================
    # LIVE DATA
    # ========================================================================

    def get_todays_games(self) -> List[Dict]:
        """Get today's games with current scores."""
        self._rate_limit()

        try:
            sb = scoreboard.ScoreBoard()
            games_data = sb.games.get_dict() if sb.games else []
            return games_data
        except Exception as e:
            raise RuntimeError(f"Failed to fetch today's games: {e}")

    def get_live_odds(self) -> Dict:
        """Get current betting odds for today's games."""
        self._rate_limit()

        try:
            live_odds = odds.Odds()
            return live_odds.games.get_dict() if live_odds.games else []
        except Exception as e:
            raise RuntimeError(f"Failed to fetch live odds: {e}")

    # ========================================================================
    # UTILITY
    # ========================================================================

    def clear_cache(self) -> int:
        """Clear all cached data."""
        if self.cache:
            return self.cache.clear()
        return 0


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def grade_shadow_card(
    picks: List[Dict],
    bridge: Optional[NBAAPIBridge] = None
) -> Dict:
    """
    Grade a complete shadow card.

    Args:
        picks: List of pick dicts with: game_id, player_name, prop_type, line, pick_direction
        bridge: Optional NBAAPIBridge instance (creates new if not provided)

    Returns:
        Dict with results, summary stats, and any errors
    """
    if bridge is None:
        bridge = NBAAPIBridge()

    results = []
    errors = []

    for pick in picks:
        try:
            result = bridge.grade_pick(
                game_id=pick['game_id'],
                player_name=pick['player_name'],
                prop_type=pick['prop_type'],
                line=pick['line'],
                pick_direction=pick['pick_direction']
            )
            if result:
                results.append(asdict(result))
            else:
                errors.append({
                    'pick': pick,
                    'error': 'Player not found in boxscore'
                })
        except Exception as e:
            errors.append({
                'pick': pick,
                'error': str(e)
            })

    # Calculate summary
    wins = sum(1 for r in results if r['result'] == 'W')
    losses = sum(1 for r in results if r['result'] == 'L')
    pushes = sum(1 for r in results if r['result'] == 'P')
    margins = [r['margin'] for r in results]

    return {
        'results': results,
        'summary': {
            'total_picks': len(picks),
            'graded': len(results),
            'wins': wins,
            'losses': losses,
            'pushes': pushes,
            'win_rate': round(wins / len(results) * 100, 1) if results else 0,
            'avg_margin': round(sum(margins) / len(margins), 2) if margins else 0
        },
        'errors': errors
    }


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='HELIOS NBA API Bridge')
    parser.add_argument('command', choices=['boxscore', 'player', '3pa', 'minutes', 'grade'])
    parser.add_argument('--game-id', help='Game ID for boxscore/grade commands')
    parser.add_argument('--player', help='Player name or ID')
    parser.add_argument('--prop', help='Prop type (PTS, REB, AST, 3PM, etc.)')
    parser.add_argument('--line', type=float, help='Betting line')
    parser.add_argument('--direction', choices=['O', 'U'], help='Over/Under')
    parser.add_argument('--games', type=int, default=20, help='Number of games to analyze')

    args = parser.parse_args()
    bridge = NBAAPIBridge()

    if args.command == 'boxscore':
        if not args.game_id:
            print("Error: --game-id required")
        else:
            box = bridge.get_boxscore(args.game_id)
            for p in box['players']:
                print(f"{p['player_name']}: {p['points']} PTS, {p['rebounds']} REB, {p['assists']} AST, {p['fg3_made']} 3PM")

    elif args.command == 'player':
        if not args.player:
            print("Error: --player required")
        else:
            player = bridge.find_player(args.player)
            print(json.dumps(player, indent=2))

    elif args.command == '3pa':
        if not args.player:
            print("Error: --player required")
        else:
            player_id = bridge.find_player_id(args.player)
            if player_id:
                stats = bridge.get_player_3pa_stats(player_id, args.games)
                print(json.dumps(asdict(stats), indent=2))
            else:
                print(f"Player not found: {args.player}")

    elif args.command == 'minutes':
        if not args.player:
            print("Error: --player required")
        else:
            player_id = bridge.find_player_id(args.player)
            if player_id:
                stats = bridge.get_player_minutes_stats(player_id, args.games)
                print(json.dumps(asdict(stats), indent=2))
            else:
                print(f"Player not found: {args.player}")

    elif args.command == 'grade':
        if not all([args.game_id, args.player, args.prop, args.line, args.direction]):
            print("Error: --game-id, --player, --prop, --line, --direction all required")
        else:
            result = bridge.grade_pick(
                game_id=args.game_id,
                player_name=args.player,
                prop_type=args.prop,
                line=args.line,
                pick_direction=args.direction
            )
            if result:
                print(json.dumps(asdict(result), indent=2))
            else:
                print("Player not found in boxscore")
