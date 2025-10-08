# game_stats.py - Game statistics and achievement tracking
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class Achievement:
    """Represents a single achievement with tracking data."""
    id: str
    name: str
    description: str
    unlocked: bool = False
    unlock_date: Optional[str] = None
    progress: int = 0
    target: int = 1
    hidden: bool = False

    def check_unlock(self, current_value: int) -> bool:
        """Check if achievement should be unlocked based on current value."""
        if not self.unlocked and current_value >= self.target:
            self.unlocked = True
            self.unlock_date = datetime.now().isoformat()
            return True
        self.progress = min(current_value, self.target)
        return False

    def get_progress_percent(self) -> float:
        """Get achievement progress as percentage."""
        return (self.progress / self.target) * 100 if self.target > 0 else 100


@dataclass
class GameStatistics:
    """Comprehensive game statistics tracking."""
    total_games: int = 0
    best_score: int = 0
    total_pipes_passed: int = 0
    total_play_time: float = 0.0
    total_flaps: int = 0
    total_deaths: int = 0
    games_this_session: int = 0
    session_start_time: float = field(default_factory=time.time)
    
    # Advanced stats
    perfect_passes: int = 0  # Through center of pipe
    close_calls: int = 0     # Near misses
    longest_survival: float = 0.0
    average_score: float = 0.0
    
    def update_game_end(self, score: int, pipes_passed: int, flaps: int, game_time: float) -> None:
        """Update statistics when a game ends."""
        self.total_games += 1
        self.games_this_session += 1
        self.total_pipes_passed += pipes_passed
        self.total_flaps += flaps
        self.total_play_time += game_time
        self.total_deaths += 1
        
        if score > self.best_score:
            self.best_score = score
        
        if game_time > self.longest_survival:
            self.longest_survival = game_time
            
        self.average_score = self.total_pipes_passed / max(1, self.total_games)

    def get_session_time(self) -> float:
        """Get current session play time."""
        return time.time() - self.session_start_time


class AchievementManager:
    """Manages achievements and their persistence."""
    
    def __init__(self, save_file: str = "achievements.json"):
        self.save_file = Path(save_file)
        self.achievements: Dict[str, Achievement] = {}
        self.newly_unlocked: List[Achievement] = []
        self._initialize_achievements()
        self.load()

    def _initialize_achievements(self) -> None:
        """Initialize all available achievements."""
        achievements_data = [
            # Basic achievements
            {"id": "first_flight", "name": "First Flight", "description": "Complete your first game", "target": 1},
            {"id": "baby_steps", "name": "Baby Steps", "description": "Pass through 5 pipes", "target": 5},
            {"id": "getting_good", "name": "Getting Good", "description": "Score 10 points", "target": 10},
            {"id": "decent_pilot", "name": "Decent Pilot", "description": "Score 25 points", "target": 25},
            {"id": "skilled_flyer", "name": "Skilled Flyer", "description": "Score 50 points", "target": 50},
            {"id": "ace_pilot", "name": "Ace Pilot", "description": "Score 100 points", "target": 100},
            
            # Skill-based achievements
            {"id": "precision_pilot", "name": "Precision Pilot", "description": "Pass 10 pipes through center", "target": 10},
            {"id": "close_call_king", "name": "Close Call King", "description": "Have 25 near misses", "target": 25},
            {"id": "efficient_flyer", "name": "Efficient Flyer", "description": "Score 20+ with less than 50 flaps", "target": 1},
            
            # Persistence achievements
            {"id": "dedicated", "name": "Dedicated", "description": "Play 50 games", "target": 50},
            {"id": "marathon_runner", "name": "Marathon Runner", "description": "Survive for 60 seconds", "target": 60},
            {"id": "century_club", "name": "Century Club", "description": "Pass 100 total pipes", "target": 100},
            
            # Hidden achievements
            {"id": "crash_test_dummy", "name": "Crash Test Dummy", "description": "Die 100 times", "target": 100, "hidden": True},
            {"id": "button_masher", "name": "Button Masher", "description": "Flap 1000 times total", "target": 1000, "hidden": True},
        ]
        
        for data in achievements_data:
            achievement = Achievement(**data)
            self.achievements[achievement.id] = achievement

    def check_achievements(self, stats: GameStatistics, current_score: int = 0, 
                          current_flaps: int = 0, game_time: float = 0.0) -> List[Achievement]:
        """Check all achievements and return newly unlocked ones."""
        self.newly_unlocked.clear()
        
        # Check each achievement
        checks = {
            "first_flight": stats.total_games,
            "baby_steps": current_score,
            "getting_good": current_score,
            "decent_pilot": current_score,
            "skilled_flyer": current_score,
            "ace_pilot": current_score,
            "precision_pilot": stats.perfect_passes,
            "close_call_king": stats.close_calls,
            "dedicated": stats.total_games,
            "marathon_runner": int(game_time),
            "century_club": stats.total_pipes_passed,
            "crash_test_dummy": stats.total_deaths,
            "button_masher": stats.total_flaps,
        }
        
        # Special achievement: efficient flyer
        if (current_score >= 20 and current_flaps < 50 and 
            self.achievements["efficient_flyer"].check_unlock(1)):
            self.newly_unlocked.append(self.achievements["efficient_flyer"])
        
        # Check standard achievements
        for achievement_id, current_value in checks.items():
            if achievement_id in self.achievements:
                if self.achievements[achievement_id].check_unlock(current_value):
                    self.newly_unlocked.append(self.achievements[achievement_id])
        
        if self.newly_unlocked:
            self.save()
        
        return self.newly_unlocked.copy()

    def get_unlocked_achievements(self) -> List[Achievement]:
        """Get all unlocked achievements."""
        return [a for a in self.achievements.values() if a.unlocked]

    def get_visible_achievements(self) -> List[Achievement]:
        """Get all non-hidden achievements."""
        return [a for a in self.achievements.values() if not a.hidden]

    def save(self) -> None:
        """Save achievements to file."""
        try:
            data = {aid: asdict(achievement) for aid, achievement in self.achievements.items()}
            with open(self.save_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save achievements: {e}")

    def load(self) -> None:
        """Load achievements from file."""
        try:
            if self.save_file.exists():
                with open(self.save_file, 'r') as f:
                    data = json.load(f)
                    for aid, achievement_data in data.items():
                        if aid in self.achievements:
                            # Update existing achievement with saved data
                            saved_achievement = Achievement(**achievement_data)
                            self.achievements[aid] = saved_achievement
        except Exception as e:
            print(f"Failed to load achievements: {e}")


class GameConfig:
    """Game configuration management with persistence."""
    
    def __init__(self, config_file: str = "game_config.json"):
        self.config_file = Path(config_file)
        self.config = {
            "sound_enabled": True,
            "music_enabled": True,
            "show_fps": False,
            "difficulty": "normal",  # easy, normal, hard
            "fullscreen": False,
            "vsync": True,
        }
        self.load()

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set configuration value and save."""
        self.config[key] = value
        self.save()

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def load(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception as e:
            print(f"Failed to load config: {e}")