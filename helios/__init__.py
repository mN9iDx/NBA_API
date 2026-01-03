"""
HELIOS NBA API Integration Module

Provides automated data fetching and analysis for the HELIOS
player prop betting system.

Components:
- nba_api_bridge: Core API wrapper with caching
- grading: Automated boxscore grading
- player_analysis: 3PA stability, minutes volatility
"""

from .nba_api_bridge import NBAAPIBridge

__all__ = ['NBAAPIBridge']
__version__ = '0.1.0'
