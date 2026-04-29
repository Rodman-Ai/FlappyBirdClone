# FlappyBirdClone — codebase guide for Claude Code

## Overview
Python/Pygame Flappy Bird clone with object pooling, surface caching, an achievement system, and async main loop for web/mobile compatibility via pygbag.

## Running locally
```bash
pip install -r requirements.txt
python main.py
```

## Building for web / mobile browsers
```bash
pip install pygbag
python -m pygbag main.py
# open http://localhost:8000 — works in any desktop or mobile browser
```

## File map

| File | Purpose |
|------|---------|
| `main.py` | Async game loop, event handling, rendering orchestration |
| `sprites.py` | `OptimizedSprite` base, `Bird`, `PipePair`, `PipePool`, collision helpers, surface cache |
| `settings.py` | All numeric constants (WIDTH, HEIGHT, physics, pipe params) |
| `game_stats.py` | `GameStatistics`, `AchievementManager`, `GameConfig` (JSON persistence) |
| `performance.py` | `EfficiencyManager`, `PerformanceMonitor`, `SurfaceCache`, `OptimizedRenderer` |

## Key design patterns

- **Object pool** — `PipePool` reuses `PipePair` instances to avoid GC pressure.
- **Dirty-flag sprite** — `OptimizedSprite` base tracks whether a sprite needs redrawing; `mark_dirty()` also clears `cached_surface`.
- **Surface cache** — `get_cached_pipe_surface()` in `sprites.py` builds per-size pipe surfaces once; `Bird` caches rotated surfaces keyed by `(angle_bucket, wing_phase)`.
- **Async loop** — `main()` is `async def` with `await asyncio.sleep(0)` at the end of each frame so pygbag can yield to the browser. On desktop `asyncio.run(main())` is transparent.
- **Adaptive quality** — `PerformanceMonitor` adjusts `quality_level` based on rolling FPS; `should_skip_effects()` gates cloud rendering and the FPS counter.

## Module-level globals in sprites.py

| Name | Type | Purpose |
|------|------|---------|
| `_cache_enabled` | `bool` | Master switch toggled by `enable_sprite_caching()` |
| `_pipe_surface_cache` | `dict` | Keyed by `(width, height, is_top)` |

Call `enable_sprite_caching(True)` once at startup and `clear_sprite_cache()` on game reset.

## Game state machine
`READY` → `PLAYING` → `PAUSED` → `PLAYING` → `GAMEOVER` → `READY`

Transitions live in `main.py` helper closures `_start_game`, `_do_flap`, `_end_game`, `_restart_game`.

## Adding a new achievement
1. Append an entry to `achievements_data` in `AchievementManager._initialize_achievements()` (`game_stats.py`).
2. Add its `id` → value mapping in `AchievementManager.check_achievements()`.

## Settings reference (settings.py)
- `WIDTH / HEIGHT` — 400 × 600 px (good portrait mobile size).
- `PIPE_GAP` — 160 px gap; increase to make easier.
- `GRAVITY / FLAP_VELOCITY` — 0.40 / -7.5; tune for feel.
- `SPAWN_MS` — 1400 ms between pipes.
