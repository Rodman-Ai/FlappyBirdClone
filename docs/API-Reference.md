# API Reference

## sprites.py

### `OptimizedSprite`
Base class for all game sprites.

| Member | Signature | Description |
|--------|-----------|-------------|
| `mark_dirty()` | `() -> None` | Invalidates `cached_surface` and sets `_dirty = True` |
| `is_dirty()` | `() -> bool` | Returns current dirty state |
| `mark_clean()` | `() -> None` | Clears dirty flag after draw |
| `cached_surface` | `Optional[Surface]` | Holds pre-rendered surface; cleared by `mark_dirty()` |

---

### `PipePair(OptimizedSprite)` — dataclass

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `x` | `float` | — | Left edge X position |
| `gap_y` | `int` | — | Vertical centre of the gap |
| `gap` | `int` | `PIPE_GAP` | Gap height in pixels |
| `width` | `int` | `PIPE_WIDTH` | Pipe width in pixels |
| `speed` | `float` | `PIPE_SPEED` | Scroll speed (px/frame at 60 fps) |
| `scored` | `bool` | `False` | True once the bird has passed this pipe |
| `active` | `bool` | `True` | False when returned to the object pool |

| Method | Signature | Description |
|--------|-----------|-------------|
| `rects()` | `() -> Tuple[Rect, Rect]` | Cached collision rects `(top, bottom)` |
| `update(dt)` | `(float) -> None` | Advance position; invalidates rect cache |
| `draw(surf)` | `(Surface) -> None` | Render using surface cache when enabled |
| `reset(x, gap_y)` | `(float, int) -> None` | Reinitialise for pool reuse |
| `deactivate()` | `() -> None` | Mark inactive; called by pool |
| `random_spawn(x)` | `(int) -> PipePair` | Static: allocate new pipe at random height |
| `random_gap_y()` | `() -> int` | Static: random gap Y without allocation |

---

### `PipePool`

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_pipe(x, gap_y)` | `(float, int) -> PipePair` | Retrieve/reset pipe from pool |
| `return_pipe(pipe)` | `(PipePair) -> None` | Return pipe to pool |
| `update_all(dt)` | `(float) -> List[PipePair]` | Update all; auto-return off-screen pipes |
| `get_collision_candidates(x, y, r)` | `(float, float, float) -> List[PipePair]` | Broad-phase X filter |
| `get_active_pipes()` | `() -> List[PipePair]` | Snapshot of active list |
| `clear()` | `() -> None` | Return all active pipes to pool |

---

### `Bird(OptimizedSprite)`

| Member | Type | Description |
|--------|------|-------------|
| `x, y` | `float` | Position |
| `vel` | `float` | Vertical velocity (positive = falling) |
| `angle` | `float` | Visual tilt in degrees |
| `flap_count` | `int` | Cumulative flaps this game |
| `wing_animation` | `float` | 0–1 wing phase, decays each frame |

| Method | Signature | Description |
|--------|-----------|-------------|
| `flap()` | `() -> None` | Apply upward impulse; trigger wing animation |
| `update(dt)` | `(float) -> None` | Apply gravity, drag, angle smoothing |
| `draw(surf)` | `(Surface) -> None` | Draw with rotated surface cache |
| `reset(x, y)` | `(int, int) -> None` | Return to initial state |
| `rect` (property) | `Rect` | Bounding rect for broad-phase checks |

---

### Module-level cache functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `enable_sprite_caching(enabled)` | `(bool) -> None` | Toggle global surface cache |
| `clear_sprite_cache()` | `() -> None` | Flush all cached pipe surfaces |
| `get_cached_pipe_surface(w, h, is_top)` | `(int, int, bool) -> Surface` | Get or generate pipe surface |

---

### Collision helpers

| Function | Signature | Returns |
|----------|-----------|---------|
| `circle_rect_collision(cx, cy, r, rect)` | `(float, float, float, Rect) -> bool` | Exact circle–AABB test |
| `fast_collision_check(bx, by, br, pipes)` | `(float, float, float, List[PipePair]) -> bool` | Check bird vs. pipe list |
| `is_perfect_pass(by, gap_y, gap)` | `(float, float, float) -> bool` | Centre-30% pass check |
| `is_close_call(by, br, gap_y, gap)` | `(float, float, float, float) -> bool` | Within 20 px of edge |

---

## game_stats.py

### `GameStatistics` — dataclass
Tracks cumulative stats. Call `update_game_end(score, pipes, flaps, time)` on each death.

Key fields: `total_games`, `best_score`, `total_flaps`, `perfect_passes`, `close_calls`, `longest_survival`.

### `AchievementManager`

| Method | Description |
|--------|-------------|
| `check_achievements(stats, score, flaps, time)` | Returns newly unlocked `Achievement` list |
| `get_unlocked_achievements()` | All unlocked achievements |
| `save() / load()` | Persist to `achievements.json` |

### `GameConfig`

| Method | Description |
|--------|-------------|
| `get(key, default)` | Read config value |
| `set(key, value)` | Write and persist to `game_config.json` |

---

## performance.py

### `EfficiencyManager`
Top-level facade. Constructed with `(screen, target_fps)`.

| Member | Type | Description |
|--------|------|-------------|
| `monitor` | `PerformanceMonitor` | FPS/memory/quality tracking |
| `renderer` | `OptimizedRenderer` | Surface cache + batch drawing |
| `update(dt, clock)` | method | Call once per frame |
| `get_performance_info()` | `-> dict` | Metrics snapshot for overlay |

### `PerformanceMonitor`

| Method | Description |
|--------|-------------|
| `should_skip_effects()` | True when `quality_level < 0.8` |
| `increment_draw_calls()` | Per-frame counter |
| `increment_collision_checks()` | Per-frame counter |

### `OptimizedRenderer`

| Method | Description |
|--------|-------------|
| `render_background_cached(color, clouds)` | Cached sky + optional clouds |
| `get_cached_surface(key, generator, *args)` | Generic surface cache |
| `batch_draw_sprites(sprites)` | Draw list of sprites via their `draw()` method |
