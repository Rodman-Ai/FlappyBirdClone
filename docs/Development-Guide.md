# Development Guide

## Prerequisites
- Python 3.8+
- `pip install -r requirements.txt`

## Project layout

```
FlappyBirdClone/
├── main.py              Async game loop
├── sprites.py           Sprite classes + collision + cache helpers
├── settings.py          Constants — tweak here first
├── game_stats.py        Stats, achievements, config persistence
├── performance.py       Profiling, adaptive quality, renderer
├── requirements.txt     Desktop dependencies
├── requirements-web.txt Web/mobile build dependencies (pygbag)
├── CLAUDE.md            Codebase guide for Claude Code
└── docs/                This documentation suite
```

## Design patterns in use

### Object Pool (`PipePool`)
Pre-allocates `PIPE_POOL_SIZE` pipes at startup. `get_pipe()` pops from the available list and calls `reset()`; `return_pipe()` deactivates and pushes back. This eliminates per-frame allocation and reduces GC pauses.

### Dirty-flag sprite (`OptimizedSprite`)
`mark_dirty()` signals that the sprite's cached surface is stale. Renderers can check `is_dirty()` to decide whether to regenerate or reuse. Currently used to invalidate `Bird.cached_surfaces` and `PipePair._cached_rects`.

### Surface cache
Two levels:
1. **Pipe surfaces** — `_pipe_surface_cache` in `sprites.py`, keyed by `(width, height, is_top)`. Pipe sizes are deterministic so the cache has very high hit rate.
2. **Bird surfaces** — per-`Bird` dict keyed by `(angle_bucket, wing_phase)`. Capped at 20 entries with oldest-first eviction.

### Adaptive quality (`PerformanceMonitor`)
Computes rolling average FPS every 30 frames. Below 80 % of target FPS, `quality_level` decreases (min 0.5); above 95 % it increases (max 1.5). `should_skip_effects()` returns `True` below 0.8, gating cloud rendering and FPS counter.

### Async game loop
`main()` is `async def` and calls `await asyncio.sleep(0)` at the end of every frame. On desktop `asyncio.run(main())` is transparent. Under pygbag this yields control back to the browser event loop, preventing the tab from freezing.

## Extending the game

### Add a new pipe pattern
Create a subclass of `PipePair` or add a factory parameter. Spawn via `PipePool.get_pipe(x, gap_y)` — the pool is type-agnostic.

### Add a new achievement
In `game_stats.py`:
1. Append to `achievements_data` in `_initialize_achievements()`.
2. Add the `id → value` entry in the `checks` dict inside `check_achievements()`.

### Add a new game state
Extend the `state` string set in `main.py` and add the corresponding render branch in the render section.

### Tune physics
All physics constants are in `settings.py`: `GRAVITY`, `FLAP_VELOCITY`, `PIPE_SPEED`, `PIPE_GAP`, `SPAWN_MS`.

## Code style
- Type hints on all public functions.
- No inline comments unless the WHY is non-obvious.
- No docstrings on private helpers.
- Prefer `Edit` over `Write` for file modifications; keep diffs small.

## Running the web build locally
```bash
pip install pygbag
python -m pygbag main.py
# Visit http://localhost:8000
```
The build process bundles `main.py` and all imports into a `.wasm` + JS package under `build/web/`.

## Profiling
Press **F1** in-game to overlay real-time metrics. To log to stdout, call `efficiency_manager.get_performance_info()` and print the dict from within the game loop.
