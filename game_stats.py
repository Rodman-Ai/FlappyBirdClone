# game_stats.py — statistics, achievements, config, and meta-progression
import json
import time
from datetime import date, datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from settings import (
    LEADERBOARD_MAX, WEEKLY_CHALLENGE_OBJECTIVES_COUNT, DAILY_STREAK_BONUS,
    CHALLENGE_OBJECTIVES, SKIN_UNLOCK_REQUIREMENTS,
)


# ---------------------------------------------------------------------------
# Achievement
# ---------------------------------------------------------------------------

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    unlocked: bool = False
    unlock_date: Optional[str] = None
    progress: int = 0
    target: int = 1
    hidden: bool = False

    def check_unlock(self, current_value: int) -> bool:
        if not self.unlocked and current_value >= self.target:
            self.unlocked = True
            self.unlock_date = datetime.now().isoformat()
            return True
        self.progress = min(current_value, self.target)
        return False

    def get_progress_percent(self) -> float:
        return (self.progress / self.target * 100) if self.target > 0 else 100.0


# ---------------------------------------------------------------------------
# Game statistics
# ---------------------------------------------------------------------------

@dataclass
class GameStatistics:
    # Cumulative
    total_games: int = 0
    best_score: int = 0
    total_pipes_passed: int = 0
    total_play_time: float = 0.0
    total_flaps: int = 0
    total_deaths: int = 0
    perfect_passes: int = 0
    close_calls: int = 0
    longest_survival: float = 0.0
    average_score: float = 0.0

    # Session
    games_this_session: int = 0
    session_start_time: float = field(default_factory=time.time)
    session_best_score: int = 0          # feature #52

    # Daily (feature #51)
    daily_best_score: int = 0
    daily_best_date: str = ""

    # Score history for graph (feature #62)
    score_history: List[int] = field(default_factory=list)

    # Local leaderboard (feature #63)
    leaderboard: List[Dict[str, Any]] = field(default_factory=list)

    # Coins & meta (features #57, #98-99)
    coin_balance: int = 0
    daily_streak: int = 0
    last_played_date: str = ""

    # Ghost run — best run frame positions (feature #95)
    best_run_frames: List[Tuple[float, float]] = field(default_factory=list)

    # Runtime (not persisted)
    current_combo: int = field(default=0, repr=False)
    current_streak: int = field(default=0, repr=False)
    combo_peak: int = field(default=0, repr=False)

    # ---------------------------------------------------------------------------
    def update_game_end(self, score: int, pipes_passed: int,
                        flaps: int, game_time: float) -> bool:
        """Update all stats at game end. Returns True if new all-time best."""
        self.total_games += 1
        self.games_this_session += 1
        self.total_pipes_passed += pipes_passed
        self.total_flaps += flaps
        self.total_play_time += game_time
        self.total_deaths += 1

        new_best = score > self.best_score
        if new_best:
            self.best_score = score

        if game_time > self.longest_survival:
            self.longest_survival = game_time

        self.average_score = self.total_pipes_passed / max(1, self.total_games)

        # Session best
        if score > self.session_best_score:
            self.session_best_score = score

        # Daily best
        today = date.today().isoformat()
        if today != self.daily_best_date:
            self.daily_best_score = 0
            self.daily_best_date = today
        if score > self.daily_best_score:
            self.daily_best_score = score

        # Score history (last 20)
        self.score_history.append(score)
        if len(self.score_history) > 20:
            self.score_history = self.score_history[-20:]

        # Combo peak
        if self.combo_peak < self.current_combo:
            self.combo_peak = self.current_combo

        # Daily login streak
        self._update_daily_streak()

        return new_best

    def _update_daily_streak(self) -> None:
        today = date.today().isoformat()
        if self.last_played_date == today:
            return
        from datetime import timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self.last_played_date == yesterday:
            self.daily_streak += 1
        else:
            self.daily_streak = 1
        self.last_played_date = today

    def add_leaderboard_entry(self, score: int, player_name: str,
                               mode: str) -> None:
        entry = {
            "score": score,
            "name": player_name or "Player",
            "mode": mode,
            "date": date.today().isoformat(),
        }
        self.leaderboard.append(entry)
        self.leaderboard.sort(key=lambda e: e["score"], reverse=True)
        self.leaderboard = self.leaderboard[:LEADERBOARD_MAX]

    def add_coins(self, amount: int) -> None:
        self.coin_balance = max(0, self.coin_balance + amount)

    def get_session_time(self) -> float:
        return time.time() - self.session_start_time

    def reset_runtime(self) -> None:
        """Reset per-run runtime counters."""
        self.current_combo = 0
        self.current_streak = 0
        self.combo_peak = 0

    def to_dict(self) -> Dict:
        d = asdict(self)
        # Strip runtime fields (not worth persisting)
        for k in ("current_combo", "current_streak", "combo_peak",
                  "session_start_time", "games_this_session",
                  "session_best_score"):
            d.pop(k, None)
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> "GameStatistics":
        # Remove keys not in the dataclass to be forward-compatible
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid}
        return cls(**filtered)


# ---------------------------------------------------------------------------
# AchievementManager
# ---------------------------------------------------------------------------

class AchievementManager:
    def __init__(self, save_file: str = "achievements.json") -> None:
        self.save_file = Path(save_file)
        self.achievements: Dict[str, Achievement] = {}
        self.newly_unlocked: List[Achievement] = []
        self._initialize_achievements()
        self.load()

    def _initialize_achievements(self) -> None:
        data = [
            # Progression
            {"id": "first_flight",  "name": "First Flight",   "description": "Complete your first game",      "target": 1},
            {"id": "baby_steps",    "name": "Baby Steps",      "description": "Pass through 5 pipes",         "target": 5},
            {"id": "getting_good",  "name": "Getting Good",    "description": "Score 10 points",              "target": 10},
            {"id": "decent_pilot",  "name": "Decent Pilot",    "description": "Score 25 points",              "target": 25},
            {"id": "skilled_flyer", "name": "Skilled Flyer",   "description": "Score 50 points",              "target": 50},
            {"id": "ace_pilot",     "name": "Ace Pilot",       "description": "Score 100 points",             "target": 100},
            # Skill
            {"id": "precision_pilot", "name": "Precision Pilot", "description": "Pass 10 pipes through center", "target": 10},
            {"id": "close_call_king", "name": "Close Call King", "description": "Have 25 near misses",          "target": 25},
            {"id": "efficient_flyer", "name": "Efficient Flyer", "description": "Score 20+ with < 50 flaps",    "target": 1},
            # Persistence
            {"id": "dedicated",       "name": "Dedicated",       "description": "Play 50 games",                "target": 50},
            {"id": "marathon_runner", "name": "Marathon Runner", "description": "Survive for 60 seconds",       "target": 60},
            {"id": "century_club",    "name": "Century Club",    "description": "Pass 100 total pipes",         "target": 100},
            # Hidden
            {"id": "crash_test_dummy","name": "Crash Test Dummy","description": "Die 100 times",               "target": 100, "hidden": True},
            {"id": "button_masher",  "name": "Button Masher",   "description": "Flap 1000 times total",        "target": 1000,"hidden": True},
            # New
            {"id": "coin_collector", "name": "Coin Collector",  "description": "Collect 50 coins",            "target": 50},
            {"id": "combo_master",   "name": "Combo Master",    "description": "Reach a ×3 combo",            "target": 3},
            {"id": "survivor",       "name": "Survivor",        "description": "Complete a Survival game",    "target": 1},
            {"id": "speedster",      "name": "Speedster",       "description": "Complete Speed Run mode",     "target": 1},
            {"id": "gold_medal",     "name": "Gold Medalist",   "description": "Earn a Gold medal (≥30)",     "target": 30},
            {"id": "challenger",     "name": "Challenger",      "description": "Complete a full Challenge session", "target": 10},
        ]
        for item in data:
            ach = Achievement(**item)
            self.achievements[ach.id] = ach

    def check_achievements(self, stats: GameStatistics,
                           current_score: int = 0,
                           current_flaps: int = 0,
                           game_time: float = 0.0,
                           combo_peak: int = 0,
                           coins_total: int = 0,
                           mode: str = "CLASSIC",
                           challenge_done: bool = False) -> List[Achievement]:
        self.newly_unlocked.clear()

        checks = {
            "first_flight":   stats.total_games,
            "baby_steps":     current_score,
            "getting_good":   current_score,
            "decent_pilot":   current_score,
            "skilled_flyer":  current_score,
            "ace_pilot":      current_score,
            "gold_medal":     current_score,
            "precision_pilot":stats.perfect_passes,
            "close_call_king":stats.close_calls,
            "dedicated":      stats.total_games,
            "marathon_runner":int(game_time),
            "century_club":   stats.total_pipes_passed,
            "crash_test_dummy":stats.total_deaths,
            "button_masher":  stats.total_flaps,
            "coin_collector": coins_total,
            "combo_master":   combo_peak,
        }

        # Standard
        for ach_id, val in checks.items():
            if ach_id in self.achievements:
                if self.achievements[ach_id].check_unlock(val):
                    self.newly_unlocked.append(self.achievements[ach_id])

        # Special: efficient flyer
        if (current_score >= 20 and current_flaps < 50 and
                self.achievements["efficient_flyer"].check_unlock(1)):
            self.newly_unlocked.append(self.achievements["efficient_flyer"])

        # Survival mode completion
        if mode == "SURVIVAL" and current_score > 0:
            if self.achievements["survivor"].check_unlock(1):
                self.newly_unlocked.append(self.achievements["survivor"])

        # Speed run completion
        if mode == "SPEEDRUN" and current_score >= 20:
            if self.achievements["speedster"].check_unlock(1):
                self.newly_unlocked.append(self.achievements["speedster"])

        # Challenge completion
        if challenge_done:
            if self.achievements["challenger"].check_unlock(10):
                self.newly_unlocked.append(self.achievements["challenger"])

        if self.newly_unlocked:
            self.save()
        return self.newly_unlocked.copy()

    def get_unlocked_achievements(self) -> List[Achievement]:
        return [a for a in self.achievements.values() if a.unlocked]

    def get_visible_achievements(self) -> List[Achievement]:
        return [a for a in self.achievements.values() if not a.hidden]

    def is_skin_unlocked(self, skin_id: str) -> bool:
        req = SKIN_UNLOCK_REQUIREMENTS.get(skin_id, "")
        if not req:
            return True
        ach = self.achievements.get(req)
        return ach is not None and ach.unlocked

    def save(self) -> None:
        try:
            data = {aid: asdict(a) for aid, a in self.achievements.items()}
            with open(self.save_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[achievements] save failed: {e}")

    def load(self) -> None:
        try:
            if self.save_file.exists():
                with open(self.save_file, "r") as f:
                    data = json.load(f)
                for aid, d in data.items():
                    if aid in self.achievements:
                        try:
                            self.achievements[aid] = Achievement(**d)
                        except Exception:
                            pass
        except Exception as e:
            print(f"[achievements] load failed: {e}")


# ---------------------------------------------------------------------------
# Weekly challenge tracker (feature #100)
# ---------------------------------------------------------------------------

class WeeklyChallengeManager:
    """Generates and tracks 7 rotating weekly objectives."""

    def __init__(self, save_file: str = "weekly_challenge.json") -> None:
        self.save_file = Path(save_file)
        self.progress: Dict[int, int] = {}  # index → current value
        self.completed: List[bool] = []
        self._week = -1
        self.objectives: List[tuple] = []
        self._refresh()
        self.load()

    def _current_week(self) -> int:
        d = date.today()
        return d.isocalendar()[1] + d.year * 100

    def _refresh(self) -> None:
        week = self._current_week()
        if week != self._week:
            self._week = week
            import random as _r
            rng = _r.Random(week)
            pool = list(CHALLENGE_OBJECTIVES)
            rng.shuffle(pool)
            self.objectives = pool[:WEEKLY_CHALLENGE_OBJECTIVES_COUNT]
            self.progress = {i: 0 for i in range(len(self.objectives))}
            self.completed = [False] * len(self.objectives)

    def update(self, event: str, amount: int = 1) -> List[int]:
        """Call with event name and amount; returns indices of newly completed objectives."""
        self._refresh()
        newly = []
        for i, (_, key, target) in enumerate(self.objectives):
            if self.completed[i]:
                continue
            if key == event:
                self.progress[i] = min(target, self.progress.get(i, 0) + amount)
                if self.progress[i] >= target:
                    self.completed[i] = True
                    newly.append(i)
        if newly:
            self.save()
        return newly

    def all_done(self) -> bool:
        return all(self.completed)

    def done_count(self) -> int:
        return sum(self.completed)

    def save(self) -> None:
        try:
            data = {"week": self._week, "progress": self.progress,
                    "completed": self.completed}
            with open(self.save_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def load(self) -> None:
        try:
            if self.save_file.exists():
                with open(self.save_file, "r") as f:
                    data = json.load(f)
                if data.get("week") == self._week:
                    self.progress = {int(k): v for k, v in data["progress"].items()}
                    self.completed = data["completed"]
        except Exception:
            pass


# ---------------------------------------------------------------------------
# GameConfig
# ---------------------------------------------------------------------------

class GameConfig:
    """Persistent game configuration."""

    DEFAULTS: Dict[str, Any] = {
        # Gameplay
        "difficulty":       "normal",
        "game_mode":        "CLASSIC",
        # Display
        "show_fps":         False,
        "show_performance": False,
        "fullscreen":       False,
        "vsync":            False,
        "fps_cap":          60,
        # Audio
        "sfx_volume":       0.5,
        "music_volume":     0.25,
        "music_enabled":    True,
        "muted":            False,
        # Cosmetics
        "active_skin":      "classic",
        "pipe_theme":       "classic",
        "bg_theme":         "day",
        "floor_theme":      "grass",
        # Accessibility
        "high_contrast":    False,
        "reduced_motion":   False,
        "colorblind":       False,
        "large_text":       False,
        "speed_mult":       1.0,
        # Meta
        "player_name":      "",
        "first_run_done":   False,
    }

    def __init__(self, config_file: str = "game_config.json") -> None:
        self.config_file = Path(config_file)
        self.config = dict(self.DEFAULTS)
        self.load()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default if default is not None
                               else self.DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def reset_to_defaults(self) -> None:
        self.config = dict(self.DEFAULTS)
        self.save()

    def save(self) -> None:
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[config] save failed: {e}")

    def load(self) -> None:
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)
                self.config.update(loaded)
        except Exception as e:
            print(f"[config] load failed: {e}")


# ---------------------------------------------------------------------------
# Persistent stats file
# ---------------------------------------------------------------------------

def load_stats(path: str = "game_stats.json") -> GameStatistics:
    p = Path(path)
    try:
        if p.exists():
            with open(p) as f:
                data = json.load(f)
            return GameStatistics.from_dict(data)
    except Exception as e:
        print(f"[stats] load failed: {e}")
    return GameStatistics()


def save_stats(stats: GameStatistics, path: str = "game_stats.json") -> None:
    try:
        with open(path, "w") as f:
            json.dump(stats.to_dict(), f, indent=2)
    except Exception as e:
        print(f"[stats] save failed: {e}")
