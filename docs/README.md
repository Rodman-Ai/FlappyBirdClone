# FlappyBirdClone — Complete Wiki

A Python/Pygame Flappy Bird clone featuring object pooling, surface caching, an achievement system, adaptive quality, and web/mobile support via pygbag.

## Contents
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Controls](#controls)
- [Configuration](#configuration)
- [Mobile & Web](#mobile--web)
- [Further Reading](#further-reading)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

Python 3.8+ required.

---

## Architecture

```
main.py          Async game loop, event handling, render orchestration
sprites.py       OptimizedSprite, Bird, PipePair, PipePool, collision helpers
settings.py      All numeric/visual constants
game_stats.py    GameStatistics, AchievementManager, GameConfig
performance.py   EfficiencyManager, PerformanceMonitor, SurfaceCache, OptimizedRenderer
```

### State machine

```
READY ──[flap/tap]──> PLAYING ──[P]──> PAUSED ──[P/tap]──> PLAYING
                         │
                     [collision]
                         │
                      GAMEOVER ──[R/tap]──> READY
```

### Object pool

`PipePool` pre-allocates `PIPE_POOL_SIZE` (default 10) `PipePair` instances. When a pipe scrolls off-screen it is returned to the pool and reused for the next spawn, avoiding repeated allocations.

### Surface cache

`get_cached_pipe_surface(width, height, is_top)` in `sprites.py` stores rendered pipe surfaces keyed by size. `Bird` caches its rotated SRCALPHA surfaces keyed by `(angle_bucket, wing_phase)`. Toggle with `enable_sprite_caching(True/False)`; flush with `clear_sprite_cache()`.

---

## Controls

| Input | Action |
|-------|--------|
| Space / Tap / Click | Flap |
| P | Pause / Resume |
| R | Restart (Game Over screen) |
| F1 | Toggle performance overlay |
| ESC | Quit |

---

## Configuration

`game_config.json` is written automatically on first run. Supported keys:

| Key | Default | Effect |
|-----|---------|--------|
| `show_fps` | `false` | Show FPS counter during play |
| `show_performance` | `false` | Show F1 performance panel on startup |
| `difficulty` | `"normal"` | Reserved for future difficulty tiers |
| `vsync` | `true` | Reserved |

---

## Mobile & Web

The game loop is an `async def` coroutine with `await asyncio.sleep(0)` at the end of each frame. This allows [pygbag](https://pygame-web.github.io/) to compile the game to WebAssembly and run it in any browser, including mobile.

```bash
pip install pygbag
python -m pygbag main.py
# Open http://localhost:8000 on desktop or mobile
```

Touch events (`pygame.FINGERDOWN`) are handled identically to mouse clicks.

---

## Further Reading

- [API Reference](API-Reference.md) — class and function signatures
- [Development Guide](Development-Guide.md) — architecture deep-dive and contributing guidelines
- [Performance Guide](Performance-Guide.md) — profiling and optimization details
- [Achievement Guide](Achievement-Guide.md) — full achievement list and unlock conditions
