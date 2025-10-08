# settings.py — enhanced game constants with comprehensive configuration
"""Game configuration constants and settings.

This module contains all tweakable game parameters including display settings,
physics constants, gameplay parameters, and visual settings.
"""
from typing import Final

# Display settings
WIDTH: Final[int] = 400
HEIGHT: Final[int] = 600
FPS: Final[int] = 60

# Environment settings
FLOOR_HEIGHT: Final[int] = 80

# Bird physics and appearance
BIRD_X: Final[int] = 80
BIRD_RADIUS: Final[int] = 16
GRAVITY: Final[float] = 0.40         # pixels per frame per frame (scaled by dt*60)
FLAP_VELOCITY: Final[float] = -7.5   # initial velocity on flap
TERMINAL_VELOCITY: Final[float] = 12.0  # maximum fall speed
WING_RESISTANCE: Final[float] = 0.98    # air resistance factor

# Pipe settings
PIPE_SPEED: Final[float] = 3.0
PIPE_WIDTH: Final[int] = 64
PIPE_GAP: Final[int] = 160
SPAWN_MS: Final[int] = 1400

# Performance settings
PIPE_POOL_SIZE: Final[int] = 10  # Number of pipes to keep in object pool

# Achievement and scoring
PERFECT_PASS_ZONE: Final[float] = 0.3  # Fraction of gap that counts as "perfect"
CLOSE_CALL_DISTANCE: Final[int] = 20   # Pixels from pipe edge for close call

# Visual settings
SKY_COLOR: Final[tuple] = (135, 206, 235)
FLOOR_COLOR: Final[tuple] = (230, 220, 200)
FLOOR_BORDER_COLOR: Final[tuple] = (180, 170, 160)
CLOUD_COLOR: Final[tuple] = (220, 240, 255)
