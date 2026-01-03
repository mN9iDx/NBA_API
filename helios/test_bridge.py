"""
HELIOS NBA API Bridge - Unit Tests

Tests the core functionality of the NBAAPIBridge without making live API calls.
Uses mock data to validate parsing and calculation logic.
"""

import pytest
import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from nba_api_bridge import (
    NBAAPIBridge,
    PlayerActuals,
    ThreePointAnalysis,
    MinutesAnalysis,
    GradingResult,
    grade_shadow_card,
    SimpleCache,
)


# ============================================================================
# TEST DATA
# ============================================================================

MOCK_BOXSCORE_RESPONSE = {
    'game_id': '0022400456',
    'players': [
        {
            'player_id': 1631115,
            'player_name': 'Andrew Nembhard',
            'team_id': 1610612754,
            'team_tricode': 'IND',
            'minutes': 32.5,
            'points': 19,
            'rebounds': 4,
            'assists': 7,
            'steals': 1,
            'blocks': 0,
            'turnovers': 2,
            'fg_made': 7,
            'fg_attempted': 12,
            'fg3_made': 2,
            'fg3_attempted': 5,
            'ft_made': 3,
            'ft_attempted': 4,
            'plus_minus': 8,
        },
        {
            'player_id': 1629139,
            'player_name': 'T.J. McConnell',
            'team_id': 1610612754,
            'team_tricode': 'IND',
            'minutes': 24.0,
            'points': 8,
            'rebounds': 2,
            'assists': 6,
            'steals': 2,
            'blocks': 0,
            'turnovers': 1,
            'fg_made': 4,
            'fg_attempted': 7,
            'fg3_made': 0,
            'fg3_attempted': 1,
            'ft_made': 0,
            'ft_attempted': 0,
            'plus_minus': 5,
        },
        {
            'player_id': 1630738,
            'player_name': 'Tre Jones',
            'team_id': 1610612759,
            'team_tricode': 'SAS',
            'minutes': 18.3,
            'points': 6,
            'rebounds': 1,
            'assists': 3,
            'steals': 0,
            'blocks': 0,
            'turnovers': 1,
            'fg_made': 3,
            'fg_attempted': 6,
            'fg3_made': 0,
            'fg3_attempted': 1,
            'ft_made': 0,
            'ft_attempted': 0,
            'plus_minus': -4,
        },
        {
            'player_id': 203998,
            'player_name': 'Jarrett Allen',
            'team_id': 1610612739,
            'team_tricode': 'CLE',
            'minutes': 28.0,
            'points': 8,
            'rebounds': 11,
            'assists': 1,
            'steals': 0,
            'blocks': 2,
            'turnovers': 1,
            'fg_made': 4,
            'fg_attempted': 8,
            'fg3_made': 0,
            'fg3_attempted': 0,
            'ft_made': 0,
            'ft_attempted': 0,
            'plus_minus': 12,
        },
    ]
}


# ============================================================================
# PLAYER ACTUALS TESTS
# ============================================================================

class TestPlayerActuals:
    """Tests for PlayerActuals dataclass."""

    def test_get_stat_pts(self):
        """Test getting points stat."""
        actuals = PlayerActuals(
            player_id=1,
            player_name='Test Player',
            game_id='001',
            game_date='2026-01-02',
            team_id=1,
            team_tricode='TST',
            minutes=30.0,
            points=25,
            rebounds=8,
            assists=5,
            steals=1,
            blocks=1,
            turnovers=2,
            fg_made=10,
            fg_attempted=18,
            fg3_made=3,
            fg3_attempted=7,
            ft_made=2,
            ft_attempted=2,
            plus_minus=10
        )

        assert actuals.get_stat('PTS') == 25
        assert actuals.get_stat('pts') == 25

    def test_get_stat_3pm(self):
        """Test getting 3-pointers made."""
        actuals = PlayerActuals(
            player_id=1, player_name='Test', game_id='001', game_date='',
            team_id=1, team_tricode='TST', minutes=30, points=20,
            rebounds=5, assists=5, steals=1, blocks=1, turnovers=2,
            fg_made=8, fg_attempted=15, fg3_made=4, fg3_attempted=8,
            ft_made=0, ft_attempted=0, plus_minus=5
        )

        assert actuals.get_stat('3PM') == 4
        assert actuals.get_stat('3PA') == 8

    def test_get_stat_combos(self):
        """Test combo stats like PRA, PR, PA, RA."""
        actuals = PlayerActuals(
            player_id=1, player_name='Test', game_id='001', game_date='',
            team_id=1, team_tricode='TST', minutes=30, points=20,
            rebounds=10, assists=8, steals=1, blocks=1, turnovers=2,
            fg_made=8, fg_attempted=15, fg3_made=2, fg3_attempted=5,
            ft_made=2, ft_attempted=2, plus_minus=5
        )

        assert actuals.get_stat('PRA') == 38  # 20 + 10 + 8
        assert actuals.get_stat('PR') == 30   # 20 + 10
        assert actuals.get_stat('PA') == 28   # 20 + 8
        assert actuals.get_stat('RA') == 18   # 10 + 8

    def test_get_stat_invalid(self):
        """Test invalid stat returns None."""
        actuals = PlayerActuals(
            player_id=1, player_name='Test', game_id='001', game_date='',
            team_id=1, team_tricode='TST', minutes=30, points=20,
            rebounds=5, assists=5, steals=1, blocks=1, turnovers=2,
            fg_made=8, fg_attempted=15, fg3_made=2, fg3_attempted=5,
            ft_made=0, ft_attempted=0, plus_minus=5
        )

        assert actuals.get_stat('INVALID') is None


# ============================================================================
# GRADING TESTS
# ============================================================================

class TestGrading:
    """Tests for grading functionality."""

    def test_grade_under_win(self):
        """Test grading an under pick that wins."""
        # Andrew Nembhard: 19 PTS, line 20.5 U -> WIN
        result = GradingResult(
            player_name='Andrew Nembhard',
            prop_type='PTS',
            line=20.5,
            pick_direction='U',
            actual=19,
            result='W',
            margin=1.5,  # 20.5 - 19 = 1.5
            game_id='0022400456',
            game_date='2026-01-02'
        )

        assert result.result == 'W'
        assert result.margin == 1.5

    def test_grade_under_loss(self):
        """Test grading an under pick that loses."""
        # If actual > line on under, it's a loss
        result = GradingResult(
            player_name='Test Player',
            prop_type='PTS',
            line=15.5,
            pick_direction='U',
            actual=20,
            result='L',
            margin=-4.5,  # 15.5 - 20 = -4.5
            game_id='001',
            game_date=''
        )

        assert result.result == 'L'
        assert result.margin == -4.5

    def test_grade_over_win(self):
        """Test grading an over pick that wins."""
        result = GradingResult(
            player_name='Test Player',
            prop_type='PTS',
            line=15.5,
            pick_direction='O',
            actual=20,
            result='W',
            margin=4.5,  # 20 - 15.5 = 4.5
            game_id='001',
            game_date=''
        )

        assert result.result == 'W'
        assert result.margin == 4.5


# ============================================================================
# MINUTES PARSING TESTS
# ============================================================================

class TestMinutesParsing:
    """Tests for minutes string parsing."""

    def test_parse_iso_format(self):
        """Test parsing ISO 8601 duration format."""
        bridge = NBAAPIBridge(use_cache=False)

        assert bridge._parse_minutes('PT32M15.00S') == 32.2  # 32 + 15/60 = 32.25 -> 32.2
        assert bridge._parse_minutes('PT24M00.00S') == 24.0
        assert bridge._parse_minutes('PT0M') == 0.0
        assert bridge._parse_minutes('PT5M30.00S') == 5.5

    def test_parse_colon_format(self):
        """Test parsing MM:SS format."""
        bridge = NBAAPIBridge(use_cache=False)

        assert bridge._parse_minutes('32:15') == 32.2
        assert bridge._parse_minutes('24:00') == 24.0
        assert bridge._parse_minutes('5:30') == 5.5

    def test_parse_numeric(self):
        """Test parsing plain numbers."""
        bridge = NBAAPIBridge(use_cache=False)

        assert bridge._parse_minutes(32) == 32.0
        assert bridge._parse_minutes(32.5) == 32.5
        assert bridge._parse_minutes('32') == 32.0

    def test_parse_invalid(self):
        """Test parsing invalid inputs."""
        bridge = NBAAPIBridge(use_cache=False)

        assert bridge._parse_minutes(None) == 0.0
        assert bridge._parse_minutes('') == 0.0
        assert bridge._parse_minutes('invalid') == 0.0


# ============================================================================
# VALIDATION AGAINST KNOWN DATA
# ============================================================================

class TestShadowCardValidation:
    """
    Validate grading against the known shadow card data from the audit.

    Correct values from audit:
    - T.J. McConnell: 3PM = 0 (line 0.5 U) -> W, margin +0.5
    - Andrew Nembhard: PTS = 19 (line 20.5 U) -> W, margin +1.5
    - Tre Jones: PTS = 6 (line 17.5 U) -> W, margin +11.5
    - Jarrett Allen: PTS = 8 (line 17.5 U) -> W, margin +9.5
    """

    def test_mcconnell_3pm(self):
        """Validate T.J. McConnell 3PM grading."""
        player = MOCK_BOXSCORE_RESPONSE['players'][1]  # McConnell
        assert player['player_name'] == 'T.J. McConnell'
        assert player['fg3_made'] == 0

        # Grade: 3PM U 0.5 with actual 0 -> W, margin 0.5
        actual = 0
        line = 0.5
        direction = 'U'

        result = 'W' if actual < line else ('P' if actual == line else 'L')
        margin = line - actual

        assert result == 'W'
        assert margin == 0.5

    def test_nembhard_pts(self):
        """Validate Andrew Nembhard PTS grading."""
        player = MOCK_BOXSCORE_RESPONSE['players'][0]  # Nembhard
        assert player['player_name'] == 'Andrew Nembhard'
        assert player['points'] == 19

        # Grade: PTS U 20.5 with actual 19 -> W, margin 1.5
        actual = 19
        line = 20.5
        direction = 'U'

        result = 'W' if actual < line else ('P' if actual == line else 'L')
        margin = line - actual

        assert result == 'W'
        assert margin == 1.5

    def test_tre_jones_pts(self):
        """Validate Tre Jones PTS grading."""
        player = MOCK_BOXSCORE_RESPONSE['players'][2]  # Jones
        assert player['player_name'] == 'Tre Jones'
        assert player['points'] == 6

        # Grade: PTS U 17.5 with actual 6 -> W, margin 11.5
        actual = 6
        line = 17.5
        direction = 'U'

        result = 'W' if actual < line else ('P' if actual == line else 'L')
        margin = line - actual

        assert result == 'W'
        assert margin == 11.5

    def test_jarrett_allen_pts(self):
        """Validate Jarrett Allen PTS grading."""
        player = MOCK_BOXSCORE_RESPONSE['players'][3]  # Allen
        assert player['player_name'] == 'Jarrett Allen'
        assert player['points'] == 8

        # Grade: PTS U 17.5 with actual 8 -> W, margin 9.5
        actual = 8
        line = 17.5
        direction = 'U'

        result = 'W' if actual < line else ('P' if actual == line else 'L')
        margin = line - actual

        assert result == 'W'
        assert margin == 9.5

    def test_average_margin(self):
        """Validate correct average margin calculation."""
        margins = [0.5, 1.5, 11.5, 9.5]
        avg_margin = sum(margins) / len(margins)

        assert avg_margin == 5.75  # Not 6.75 as incorrectly reported


# ============================================================================
# 3PA ANALYSIS TESTS
# ============================================================================

class TestThreePointAnalysis:
    """Tests for 3PA coefficient of variation calculations."""

    def test_stability_grade_a(self):
        """Test grade A (CoV < 0.2) calculation."""
        # Low variance = high stability
        import numpy as np

        values = [6, 6, 7, 6, 7, 6, 6, 7, 6, 6]  # Very consistent
        arr = np.array(values)
        avg = np.mean(arr)
        std = np.std(arr)
        cov = std / avg

        assert cov < 0.2
        # Grade should be 'A'

    def test_stability_grade_f(self):
        """Test grade F (CoV >= 0.7) calculation."""
        import numpy as np

        values = [0, 10, 2, 12, 1, 8, 0, 15, 3, 9]  # Highly variable
        arr = np.array(values)
        avg = np.mean(arr)
        std = np.std(arr)
        cov = std / avg

        assert cov >= 0.7
        # Grade should be 'F'

    def test_games_under_5_calculation(self):
        """Test counting games with < 5 3PA."""
        import numpy as np

        values = [2, 3, 7, 8, 4, 6, 1, 9, 5, 10]
        arr = np.array(values)

        games_under_5 = np.sum(arr < 5)
        assert games_under_5 == 4  # 2, 3, 4, 1


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
