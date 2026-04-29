# Performance Guide

## Target metrics
| Metric | Goal |
|--------|------|
| Frame rate | 60 FPS stable |
| Memory | < 100 MB RSS |
| Collision checks/frame | ≤ 2 (only pipes in X range) |
| Surface cache hit rate | > 95 % after first few frames |

---

## Techniques used

### 1. Object pooling — `PipePool`
`PipePair` instances are reused across spawns rather than allocated and garbage-collected every 1.4 seconds. The pool pre-warms `PIPE_POOL_SIZE` pipes at startup; at steady state, no heap allocations occur for pipes.

**Tuning:** Increase `PIPE_POOL_SIZE` in `settings.py` if you reduce `SPAWN_MS` significantly.

### 2. Pipe surface cache — `get_cached_pipe_surface`
Pipe rectangles have a fixed set of possible heights (determined by `PIPE_GAP` and the range of `gap_y` values). The first time a pipe of a given `(width, height, is_top)` combination is drawn, its surface is rendered into `_pipe_surface_cache`. Subsequent draws are `Surface.blit` — no `pygame.draw.rect` calls.

**Expected hit rate:** 100 % after the first pipe of each unique height has been drawn.

### 3. Bird surface cache — `Bird.cached_surfaces`
Rotating an SRCALPHA surface is expensive. The bird's angle is quantised to 5-degree buckets and the wing phase to 1 decimal place, giving ~30 distinct cache keys in practice. Entries are evicted LRU-style once the cache exceeds 20 entries.

### 4. Rect caching — `PipePair._cached_rects`
Collision rectangles are recomputed only when `x` changes by ≥ 1 pixel. At 60 FPS this means the cache is valid for the full frame in which the pipe did not move (e.g., while paused).

### 5. Broad-phase collision filtering — `PipePool.get_collision_candidates`
Only pipes whose X range overlaps the bird's bounding box are passed to `fast_collision_check`. At most 1–2 pipes can be in range at any time, so the precise circle–AABB test runs ≤ 4 times per frame.

### 6. Background caching — `OptimizedRenderer.render_background_cached`
The static sky + clouds background is rendered once and reused every frame. A hash of `(sky_color, clouds_enabled)` detects changes; only then is the background regenerated.

### 7. Adaptive quality — `PerformanceMonitor`
Rolling 30-frame FPS average drives `quality_level`:
- **≥ 95 % of target** → quality creeps up toward 1.5 (enhanced effects).
- **< 80 % of target** → quality drops toward 0.5 (effects disabled).
- `should_skip_effects()` returns `True` below 0.8, disabling cloud rendering and the FPS counter.

---

## Profiling in-game

Press **F1** to show the overlay:

```
FPS: 60.0
Frame: 16.7 ms
Mem: 42.3 MB
CPU: 3.1%
Quality: 1.00
Cache hit: 98%
Draw calls: 1
```

`Mem` and `CPU` fields are blank on web builds (psutil unavailable in WebAssembly).

---

## Bottleneck checklist

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| FPS drops on pipe spawn | Pool exhausted | Increase `PIPE_POOL_SIZE` |
| High mem, cache hit 0 % | Cache disabled | Check `enable_sprite_caching(True)` was called |
| Jerky bird rotation | Too many cache misses | Increase angle bucket size in `Bird.draw()` |
| Browser tab freezes | Missing `await asyncio.sleep(0)` | Verify it's at end of game loop |
