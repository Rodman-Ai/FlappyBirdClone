# settings.py — enhanced game constants with comprehensive configuration
from typing import Final, Dict, Any

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
WIDTH: Final[int] = 400
HEIGHT: Final[int] = 600
FPS: Final[int] = 60

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
FLOOR_HEIGHT: Final[int] = 80

# ---------------------------------------------------------------------------
# Bird physics
# ---------------------------------------------------------------------------
BIRD_X: Final[int] = 80
BIRD_RADIUS: Final[int] = 16
GRAVITY: Final[float] = 0.40
FLAP_VELOCITY: Final[float] = -7.5
TERMINAL_VELOCITY: Final[float] = 12.0
WING_RESISTANCE: Final[float] = 0.98

# ---------------------------------------------------------------------------
# Pipe settings
# ---------------------------------------------------------------------------
PIPE_SPEED: Final[float] = 3.0
PIPE_WIDTH: Final[int] = 64
PIPE_GAP: Final[int] = 160
SPAWN_MS: Final[int] = 1400

# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
PIPE_POOL_SIZE: Final[int] = 10
SURFACE_CACHE_MAX: Final[int] = 200   # evict LRU 25% above this

# ---------------------------------------------------------------------------
# Collision / scoring helpers
# ---------------------------------------------------------------------------
PERFECT_PASS_ZONE: Final[float] = 0.3
CLOSE_CALL_DISTANCE: Final[int] = 20

# ---------------------------------------------------------------------------
# Medal thresholds
# ---------------------------------------------------------------------------
MEDAL_BRONZE: Final[int] = 5
MEDAL_SILVER: Final[int] = 15
MEDAL_GOLD: Final[int] = 30
MEDAL_PLATINUM: Final[int] = 60

# ---------------------------------------------------------------------------
# Dynamic difficulty (feature #29)
# ---------------------------------------------------------------------------
DYNAMIC_DIFF_INTERVAL: Final[int] = 10   # pipes between each tick
DYNAMIC_DIFF_SPEED_INC: Final[float] = 0.10
DYNAMIC_DIFF_GAP_DEC: Final[int] = 2
MAX_PIPE_SPEED: Final[float] = 6.0
MIN_PIPE_GAP: Final[int] = 100

# Difficulty preset offsets applied at game start (feature #28)
DIFFICULTY_PRESETS: Final[Dict[str, Dict[str, Any]]] = {
    "easy":   {"gap_offset": +40, "speed_mult": 0.85, "spawn_offset_ms": +200},
    "normal": {"gap_offset":   0, "speed_mult": 1.00, "spawn_offset_ms":    0},
    "hard":   {"gap_offset": -40, "speed_mult": 1.20, "spawn_offset_ms": -200},
}

# ---------------------------------------------------------------------------
# Power-ups (features #53-58)
# ---------------------------------------------------------------------------
POWERUP_SPAWN_CHANCE: Final[float] = 0.15  # per pipe gap
POWERUP_SLOWMO_DURATION: Final[float] = 5.0
POWERUP_TINY_DURATION: Final[float] = 8.0
POWERUP_WIDEGAP_PIPES: Final[int] = 3
POWERUP_RADIUS: Final[int] = 10

POWERUP_TYPES = ("shield", "slowmo", "tiny", "widegap")
POWERUP_COLORS: Final[Dict[str, tuple]] = {
    "shield":  (100, 200, 255),
    "slowmo":  (180, 100, 255),
    "tiny":    (100, 255, 180),
    "widegap": (255, 200, 80),
}
POWERUP_LABELS: Final[Dict[str, str]] = {
    "shield":  "S",
    "slowmo":  "T",
    "tiny":    "↓",
    "widegap": "↕",
}

# ---------------------------------------------------------------------------
# Coins (features #57, #98)
# ---------------------------------------------------------------------------
COIN_SPAWN_CHANCE: Final[float] = 0.40
COIN_RADIUS: Final[int] = 8
COIN_VALUE: Final[int] = 1

# ---------------------------------------------------------------------------
# Game modes (features #38-45)
# ---------------------------------------------------------------------------
GAME_MODES = ("CLASSIC", "TIME_ATTACK", "SURVIVAL", "ZEN", "NIGHT",
              "TINY_BIRD", "TURBO", "PRACTICE", "CHALLENGE", "SPEEDRUN")

GAME_MODE_LABELS: Final[Dict[str, str]] = {
    "CLASSIC":    "Classic",
    "TIME_ATTACK":"Time Attack",
    "SURVIVAL":   "Survival",
    "ZEN":        "Zen",
    "NIGHT":      "Night",
    "TINY_BIRD":  "Tiny Bird",
    "TURBO":      "Turbo",
    "PRACTICE":   "Practice",
    "CHALLENGE":  "Challenge",
    "SPEEDRUN":   "Speed Run",
}

GAME_MODE_DESCS: Final[Dict[str, str]] = {
    "CLASSIC":    "Infinite classic play",
    "TIME_ATTACK":"Max score in 60 seconds",
    "SURVIVAL":   "3 lives — perfect passes restore 1",
    "ZEN":        "No collision — how far can you go?",
    "NIGHT":      "Dark theme, same challenge",
    "TINY_BIRD":  "Smaller bird, same pipes",
    "TURBO":      "2× speed, 2× score",
    "PRACTICE":   "Unlimited lives, no saving",
    "CHALLENGE":  "10 micro-objectives per session",
    "SPEEDRUN":   f"Score 20 pipes as fast as possible",
}

TIME_ATTACK_DURATION: Final[float] = 60.0
SURVIVAL_LIVES: Final[int] = 3
TURBO_SPEED_MULT: Final[float] = 2.0
TURBO_SCORE_MULT: Final[int] = 2
TINY_BIRD_RADIUS_REDUCTION: Final[int] = 6
SPEEDRUN_TARGET_SCORE: Final[int] = 20

# Challenge objectives (feature #42) — cycled 10 per session
CHALLENGE_OBJECTIVES = [
    ("Pass 5 pipes", "pipes", 5),
    ("Score 3 perfect passes", "perfects", 3),
    ("Have 2 close calls", "close_calls", 2),
    ("Pass 10 pipes", "pipes", 10),
    ("Score 5 perfect passes", "perfects", 5),
    ("Flap 30 times", "flaps", 30),
    ("Pass 3 pipes", "pipes", 3),
    ("Score 2 perfect passes", "perfects", 2),
    ("Pass 8 pipes", "pipes", 8),
    ("Have 1 close call", "close_calls", 1),
]

# Countdown duration before play (feature #34)
COUNTDOWN_DURATION: Final[int] = 3

# ---------------------------------------------------------------------------
# Rare pipe variants (features #31-32)
# ---------------------------------------------------------------------------
WIDE_GAP_CHANCE: Final[float] = 0.12     # 1-in-~8
NARROW_GAP_CHANCE: Final[float] = 0.10   # 1-in-10
WIDE_GAP_MULT: Final[float] = 1.5
NARROW_GAP_MULT: Final[float] = 0.70
NARROW_GAP_BONUS: Final[int] = 2         # extra points

# Moving pipes (feature #33) — enabled in some modes
MOVING_PIPE_AMPLITUDE: Final[int] = 30   # pixels
MOVING_PIPE_FREQ: Final[float] = 0.8     # Hz

# First-pipe grace extra gap (feature #35)
FIRST_PIPE_GRACE: Final[int] = 40

# ---------------------------------------------------------------------------
# Visuals — base colors
# ---------------------------------------------------------------------------
SKY_COLOR: Final[tuple] = (135, 206, 235)
FLOOR_COLOR: Final[tuple] = (230, 220, 200)
FLOOR_BORDER_COLOR: Final[tuple] = (180, 170, 160)
CLOUD_COLOR: Final[tuple] = (220, 240, 255)

# ---------------------------------------------------------------------------
# Theme palettes (features #23-25)
# ---------------------------------------------------------------------------
PIPE_THEMES: Final[Dict[str, Dict[str, tuple]]] = {
    "classic": {"fill": (80, 200, 120), "dark": (40, 120, 80),  "mid": (100, 200, 130)},
    "ice":     {"fill": (100, 180, 240),"dark": (50, 100, 180), "mid": (120, 200, 255)},
    "lava":    {"fill": (220, 80, 60),  "dark": (150, 40, 20),  "mid": (240, 120, 80)},
    "gold":    {"fill": (220, 180, 40), "dark": (160, 120, 10), "mid": (240, 200, 80)},
}

BG_THEMES: Final[Dict[str, Dict[str, Any]]] = {
    "day":    {"sky": (135, 206, 235), "clouds": (220, 240, 255), "stars": False},
    "sunset": {"sky": (255, 150, 80),  "clouds": (255, 200, 150), "stars": False},
    "night":  {"sky": (15,  15,  40),  "clouds": (30,  30,  60),  "stars": True},
    "storm":  {"sky": (70,  80,  95),  "clouds": (55,  65,  80),  "stars": False},
}

FLOOR_THEMES: Final[Dict[str, Dict[str, tuple]]] = {
    "grass": {"fill": (230, 220, 200), "border": (180, 170, 160)},
    "snow":  {"fill": (235, 245, 255), "border": (190, 210, 230)},
    "sand":  {"fill": (240, 210, 150), "border": (200, 170, 110)},
    "lava":  {"fill": (200, 80,  40),  "border": (150, 40,  10)},
}

# ---------------------------------------------------------------------------
# Bird skins (features #21-22) — procedurally drawn
# ---------------------------------------------------------------------------
BIRD_SKINS: Final[Dict[str, Dict[str, tuple]]] = {
    "classic": {"body": (250, 210, 70),  "outline": (200, 160, 20),
                "wing": (220, 180, 40),  "eye_bg": (255, 255, 255),
                "pupil": (0, 0, 0),      "beak": (240, 150, 0)},
    "red":     {"body": (230, 80,  60),  "outline": (180, 40,  20),
                "wing": (210, 60,  40),  "eye_bg": (255, 255, 255),
                "pupil": (0, 0, 0),      "beak": (240, 150, 0)},
    "blue":    {"body": (80,  150, 230), "outline": (40,  100, 180),
                "wing": (60,  130, 210), "eye_bg": (255, 255, 255),
                "pupil": (0, 0, 0),      "beak": (240, 150, 0)},
    "robot":   {"body": (180, 180, 200), "outline": (100, 100, 140),
                "wing": (150, 150, 180), "eye_bg": (0,   255, 200),
                "pupil": (0, 180, 120),  "beak": (150, 150, 150)},
    "ghost":   {"body": (240, 240, 255), "outline": (180, 180, 220),
                "wing": (210, 210, 240), "eye_bg": (80,  0,   150),
                "pupil": (40, 0, 100),   "beak": (200, 150, 200)},
    "fire":    {"body": (230, 120, 20),  "outline": (180, 60,  10),
                "wing": (255, 80,  0),   "eye_bg": (255, 255, 0),
                "pupil": (180, 0, 0),    "beak": (240, 150, 0)},
}

SKIN_UNLOCK_REQUIREMENTS: Final[Dict[str, str]] = {
    "classic": "",               # always unlocked
    "red":     "getting_good",   # score 10
    "blue":    "decent_pilot",   # score 25
    "robot":   "skilled_flyer",  # score 50
    "ghost":   "dedicated",      # 50 games
    "fire":    "ace_pilot",      # score 100
}

# ---------------------------------------------------------------------------
# UI constants (feature #59-68)
# ---------------------------------------------------------------------------
BUTTON_H: Final[int] = 44
BUTTON_COLOR: Final[tuple] = (50, 110, 200)
BUTTON_HOVER: Final[tuple] = (70, 140, 240)
BUTTON_PRESSED: Final[tuple] = (30, 80, 160)
BUTTON_TEXT: Final[tuple] = (255, 255, 255)
PANEL_BG: Final[tuple] = (20, 22, 38)
PANEL_BORDER: Final[tuple] = (60, 70, 120)
TITLE_COLOR: Final[tuple] = (255, 220, 60)
SUBTITLE_COLOR: Final[tuple] = (180, 200, 255)
MUTED_COLOR: Final[tuple] = (120, 130, 160)
SUCCESS_COLOR: Final[tuple] = (80, 220, 100)
WARNING_COLOR: Final[tuple] = (255, 180, 50)
DANGER_COLOR: Final[tuple] = (255, 80, 80)

# ---------------------------------------------------------------------------
# Accessibility defaults (features #69-75)
# ---------------------------------------------------------------------------
DEFAULT_HIGH_CONTRAST: Final[bool] = False
DEFAULT_REDUCED_MOTION: Final[bool] = False
DEFAULT_COLORBLIND: Final[bool] = False
DEFAULT_LARGE_TEXT: Final[bool] = False
DEFAULT_ALWAYS_FPS: Final[bool] = False
DEFAULT_SPEED_MULT: Final[float] = 1.0   # 0.5–1.5×

# ---------------------------------------------------------------------------
# Audio defaults (features #1-6)
# ---------------------------------------------------------------------------
DEFAULT_SFX_VOLUME: Final[float] = 0.5
DEFAULT_MUSIC_VOLUME: Final[float] = 0.25
DEFAULT_MUTED: Final[bool] = False

# ---------------------------------------------------------------------------
# Technical defaults (features #76-87)
# ---------------------------------------------------------------------------
DEFAULT_FULLSCREEN: Final[bool] = False
DEFAULT_VSYNC: Final[bool] = False
DEFAULT_FPS_CAP: Final[int] = 60     # 30 / 60 / 0=unlimited
DEFAULT_SHOW_FPS: Final[bool] = False
DEFAULT_SHOW_PERF: Final[bool] = False

# Weekly challenge seed offset (feature #100)
WEEKLY_CHALLENGE_OBJECTIVES_COUNT: Final[int] = 7

# Daily login streak bonus coins (feature #99)
DAILY_STREAK_BONUS: Final[int] = 5

# Leaderboard max entries (feature #63)
LEADERBOARD_MAX: Final[int] = 10
