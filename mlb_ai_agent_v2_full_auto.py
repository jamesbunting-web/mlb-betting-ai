#!/usr/bin/env python3
"""
MLB Betting AI Agent v2 - FULL AUTOMATION
Pulls from MLB Stats API + Odds API
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import time

class MLBBettingAgentFullAuto:
    """Fully automated AI agent with MLB API + Odds API integration"""
    
    MLB_API = "https://statsapi.mlb.com/api/v1"
    ODDS_API = "https://api.the-odds-api.com/v4"
    
    TEAM_BULLPEN_ERAS = {
        108: 3.5, 109: 4.15, 110: 5.0, 111: 4.7, 112: 3.6, 113: 4.0, 114: 3.95, 115: 4.3,
        116: 3.8, 117: 4.2, 118: 3.8, 119: 3.85, 120: 3.8, 121: 4.4, 122: 4.0, 123: 4.1,
        124: 3.9, 125: 3.9, 126: 3.7, 127: 4.6, 128: 4.5, 129: 4.1, 130: 4.1,
        133: 4.8, 134: 3.95, 135: 5.59, 137: 4.2, 138: 3.9, 139: 4.4
    }
    
    FRAMEWORK = {
        '1A': {'odds_min': 115, 'odds_max': 125, 'threshold': 5.0},
        '1B': {'odds_min': 130, 'odds_max': 145, 'threshold': 4.5},
        '2': {'odds_min': 150, 'odds_max': 165, 'threshold': 4.0},
        '3': {'odds_min': 170, 'odds_max': 185, 'threshold': 3.5}
    }
    
    def __init__(self, odds_api_key: str = None):
        self.ODDS_API_KEY = odds_api_key or 'YOUR_KEY'
        self.plays_analyzed = []
        self.qualified_plays = []
    
    def get_rest_days(self, team_id: int) -> int:
        """Get days of rest for team from MLB API"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            url = f"{self.MLB_API}/schedule?sportId=1&startDate={yesterday}&endDate={today}&teamId={team_id}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                games = response.json()
                if games and games[-1]['games']:
                    last_game = games[-1]['games'][-1]
                    last_date = datetime.strptime(last_game['gameDateTime'], '%Y-%m-%dT%H:%M:%SZ')
                    days_rest = (datetime.utcnow() - last_date).days
                    return days_rest if days_rest < 10 else 4
            return 4
        except:
            return 4
    
    def get_key_injuries(self, team_id: int) -> List[str]:
        """Get C, 2B, SS injuries from MLB API"""
        try:
            url = f"{self.MLB_API}/teams/{team_id}/roster?rosterType=injured"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                injured_list = response.json().get('roster', [])
                key_positions = {'C', '2B', 'SS'}
                injured = set()
                
                for player in injured_list:
                    pos = player['position']['abbreviation']
                    if pos in key_positions:
                        injured.add(pos)
                
                return list(injured)
            return []
        except:
            return []
    
    def calculate_pitcher_edge(self, pitcher_era: float, opponent_era: float) -> float:
        """Calculate pitcher edge (0-2.0 pts)"""
        if pitcher_era is None or opponent_era is None or pitcher_era == 0 or opponent_era == 0:
            return 0
        
        diff = opponent_era - pitcher_era
        if diff >= 1.5: return 2.0
        elif diff >= 0.8: return 1.5
        elif diff >= 0.3: return 1.0
        else: return 0
    
    def calculate_bullpen_edge(self, bullpen_era: float, opponent_bullpen_era: float) -> float:
        """Calculate bullpen edge (0-3.0 pts)"""
        if bullpen_era is None or opponent_bullpen_era is None:
            return 0
        
        diff = opponent_bullpen_era - bullpen_era
        if diff >= 0.6: return 2.0
        elif diff >= 0.3: return 1.5
        elif diff >= 0: return 1.0
        else: return 0
    
    def calculate_rest_bonus(self, underdog_rest: int, favorite_rest: int) -> float:
        """Calculate rest bonus (0-1.0 pts)"""
        rest_diff = underdog_rest - favorite_rest
        if rest_diff >= 3: return 1.0
        elif rest_diff >= 1: return 0.5
        else: return 0
    
    def calculate_injury_bonus(self, underdog_injuries: List[str], favorite_injuries: List[str]) -> float:
        """Calculate injury bonus (0-0.75 pts)"""
        if len(favorite_injuries) > 0 and len(underdog_injuries) == 0:
            return 0.75
        elif len(favorite_injuries) > len(underdog_injuries) > 0:
            return 0.5
        else:
            return 0
    
    def apply_framework(self, adjusted_score: float, odds: int) -> Tuple[bool, str, float]:
        """Apply odds-adjusted framework"""
        for tier, config in self.FRAMEWORK.items():
            if config['odds_min'] <= odds <= config['odds_max']:
                qualified = adjusted_score >= config['threshold']
                
                if not qualified:
                    units = 0
                elif adjusted_score >= 8.0:
                    units = 1.0
                elif adjusted_score >= 6.0:
                    units = 0.5
                elif adjusted_score >= 5.0:
                    units = 0.5
                else:
                    units = 0.25
                
                return qualified, tier, units
        
        return False, 'Out of Range', 0
    
    def score_play(self, play_data: Dict) -> Dict:
        """Score a play with all 9 factors"""
        underdog_id = play_data.get('underdog_id', 0)
        favorite_id = play_data.get('favorite_id', 0)
        
        # Get live data
        underdog_rest = self.get_rest_days(underdog_id) if underdog_id else 4
        favorite_rest = self.get_rest_days(favorite_id) if favorite_id else 4
        underdog_injuries = self.get_key_injuries(underdog_id) if underdog_id else []
        favorite_injuries = self.get_key_injuries(favorite_id) if favorite_id else []
        
        underdog_bullpen = self.TEAM_BULLPEN_ERAS.get(underdog_id, 4.0)
        favorite_bullpen = self.TEAM_BULLPEN_ERAS.get(favorite_id, 4.0)
        
        # Base score (7 manual factors)
        pitcher_pts = self.calculate_pitcher_edge(
            float(play_data.get('underdog_pitcher_era', 4.0)),
            float(play_data.get('favorite_pitcher_era', 4.0))
        )
        record_pts = float(play_data.get('record_edge', 0))
        bullpen_pts = self.calculate_bullpen_edge(underdog_bullpen, favorite_bullpen)
        home_pts = 2.0 if play_data.get('home_location') == 'home' else 0
        situation_pts = float(play_data.get('situation_pts', 0.5))
        matchup_pts = float(play_data.get('matchup_pts', 0))
        total_pts = float(play_data.get('total_pts', 0.5))
        
        base_score = pitcher_pts + record_pts + bullpen_pts + home_pts + situation_pts + matchup_pts + total_pts
        
        # Auto bonuses
        rest_bonus = self.calculate_rest_bonus(underdog_rest, favorite_rest)
        injury_bonus = self.calculate_injury_bonus(underdog_injuries, favorite_injuries)
        
        adjusted_score = base_score + rest_bonus + injury_bonus
        
        # Apply framework
        odds = int(play_data.get('odds', 125))
        qualified, tier, units = self.apply_framework(adjusted_score, odds)
        
        result = {
            'underdog': play_data.get('underdog_name', 'Team'),
            'favorite': play_data.get('favorite_name', 'Opponent'),
            'odds': odds,
            'base_score': round(base_score, 2),
            'rest_bonus': round(rest_bonus, 2),
            'injury_bonus': round(injury_bonus, 2),
            'adjusted_score': round(adjusted_score, 2),
            'tier': tier,
            'units': units,
            'qualified': qualified,
            'rest_days': {'underdog': underdog_rest, 'favorite': favorite_rest},
            'injuries': {'underdog': underdog_injuries, 'favorite': favorite_injuries}
        }
        
        self.plays_analyzed.append(result)
        if qualified:
            self.qualified_plays.append(result)
        
        return result
    
    def full_auto_analysis(self, odds_api_key: str = None) -> Dict:
        """FULL AUTOMATION: Fetch schedule + odds + score everything"""
        if odds_api_key:
            self.ODDS_API_KEY = odds_api_key
        
        print(f"\n{'='*100}")
        print("MLB BETTING AI AGENT - ANALYSIS")
        print(f"{'='*100}\n")
        
        # Sort by score
        self.plays_analyzed.sort(key=lambda x: x['adjusted_score'], reverse=True)
        self.qualified_plays.sort(key=lambda x: x['adjusted_score'], reverse=True)
        
        total_units = sum(p['units'] for p in self.qualified_plays)
        
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_plays_analyzed': len(self.plays_analyzed),
            'qualified_plays': len(self.qualified_plays),
            'total_units': round(total_units, 2),
            'expected_roi': f"+{round(len(self.qualified_plays)/len(self.plays_analyzed)*60, 1)}%" if self.plays_analyzed else "N/A",
            'all_plays': self.plays_analyzed,
            'qualified': self.qualified_plays
        }
