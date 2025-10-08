# performance.py - Performance optimization utilities and profiling
"""Performance optimization utilities for enhanced game efficiency.

This module provides tools for:
- Surface caching and pre-rendering
- Performance monitoring and profiling
- Adaptive quality settings
- Memory usage optimization
"""
import pygame
import time
import psutil
import os
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class PerformanceMetrics:
    """Container for performance monitoring data."""
    fps: float = 0.0
    frame_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    draw_calls: int = 0
    collision_checks: int = 0
    surface_cache_hits: int = 0
    surface_cache_misses: int = 0


class PerformanceMonitor:
    """Real-time performance monitoring and adaptive quality management."""
    
    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.metrics = PerformanceMetrics()
        self.frame_times: list = []
        self.max_frame_history = 60  # Keep 1 second of frame data
        
        # Adaptive quality settings
        self.quality_level = 1.0  # 0.5 = low, 1.0 = normal, 1.5 = high
        self.auto_adjust_quality = True
        
        # Performance thresholds
        self.fps_threshold_low = target_fps * 0.8  # 80% of target
        self.fps_threshold_high = target_fps * 0.95  # 95% of target
        
        # Process monitoring
        self.process = psutil.Process(os.getpid())
        
    def update(self, dt: float, clock: pygame.time.Clock) -> None:
        """Update performance metrics."""
        # Frame timing
        self.metrics.frame_time = dt
        self.metrics.fps = clock.get_fps()
        self.frame_times.append(dt)
        
        # Keep only recent frame times
        if len(self.frame_times) > self.max_frame_history:
            self.frame_times.pop(0)
        
        # System resource usage (update less frequently for performance)
        if len(self.frame_times) % 30 == 0:  # Every 30 frames
            self.metrics.memory_usage = self.process.memory_info().rss / 1024 / 1024  # MB
            self.metrics.cpu_usage = self.process.cpu_percent()
        
        # Adaptive quality adjustment
        if self.auto_adjust_quality and len(self.frame_times) >= 30:
            self._adjust_quality()
    
    def _adjust_quality(self) -> None:
        """Automatically adjust quality based on performance."""
        avg_fps = 1.0 / (sum(self.frame_times[-30:]) / 30) if self.frame_times else 60
        
        if avg_fps < self.fps_threshold_low and self.quality_level > 0.5:
            # Reduce quality if FPS is too low
            self.quality_level = max(0.5, self.quality_level - 0.1)
        elif avg_fps > self.fps_threshold_high and self.quality_level < 1.5:
            # Increase quality if FPS is stable
            self.quality_level = min(1.5, self.quality_level + 0.05)
    
    def should_skip_effects(self) -> bool:
        """Determine if expensive effects should be skipped."""
        return self.quality_level < 0.8
    
    def get_particle_count_multiplier(self) -> float:
        """Get multiplier for particle effects based on quality."""
        return self.quality_level
    
    def reset_counters(self) -> None:
        """Reset per-frame counters."""
        self.metrics.draw_calls = 0
        self.metrics.collision_checks = 0
    
    def increment_draw_calls(self) -> None:
        """Increment draw call counter."""
        self.metrics.draw_calls += 1
    
    def increment_collision_checks(self) -> None:
        """Increment collision check counter."""
        self.metrics.collision_checks += 1


class SurfaceCache:
    """Efficient surface caching system to reduce redundant rendering."""
    
    def __init__(self, max_cache_size: int = 50):
        self.cache: Dict[str, pygame.Surface] = {}
        self.access_times: Dict[str, float] = {}
        self.max_cache_size = max_cache_size
        self.hits = 0
        self.misses = 0
    
    def get_key(self, *args) -> str:
        """Generate cache key from arguments."""
        return "|".join(str(arg) for arg in args)
    
    def get(self, key: str) -> Optional[pygame.Surface]:
        """Get surface from cache."""
        if key in self.cache:
            self.access_times[key] = time.time()
            self.hits += 1
            return self.cache[key].copy()  # Return copy to prevent modification
        self.misses += 1
        return None
    
    def put(self, key: str, surface: pygame.Surface) -> None:
        """Store surface in cache."""
        # Clean cache if it's getting too large
        if len(self.cache) >= self.max_cache_size:
            self._cleanup_cache()
        
        self.cache[key] = surface.copy()
        self.access_times[key] = time.time()
    
    def _cleanup_cache(self) -> None:
        """Remove least recently used items from cache."""
        if not self.access_times:
            return
        
        # Remove oldest 25% of cache entries
        sorted_items = sorted(self.access_times.items(), key=lambda x: x[1])
        items_to_remove = len(sorted_items) // 4
        
        for key, _ in sorted_items[:items_to_remove]:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
    
    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Tuple[int, int, float]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        return self.hits, self.misses, hit_rate


class OptimizedRenderer:
    """Optimized rendering system with dirty rectangles and batching."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.dirty_rects: list = []
        self.surface_cache = SurfaceCache()
        self.background_cache: Optional[pygame.Surface] = None
        self.last_background_hash = None
        
    def mark_dirty(self, rect: pygame.Rect) -> None:
        """Mark a screen area as needing redraw."""
        self.dirty_rects.append(rect)
    
    def clear_dirty_rects(self) -> None:
        """Clear dirty rectangle list."""
        self.dirty_rects.clear()
    
    def get_cached_surface(self, cache_key: str, generator_func, *args) -> pygame.Surface:
        """Get surface from cache or generate it."""
        cached = self.surface_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Generate new surface
        surface = generator_func(*args)
        self.surface_cache.put(cache_key, surface)
        return surface
    
    def render_background_cached(self, sky_color: tuple, clouds: bool = True) -> pygame.Surface:
        """Render background with caching."""
        bg_hash = hash((sky_color, clouds))
        
        if (self.background_cache is not None and 
            self.last_background_hash == bg_hash):
            return self.background_cache
        
        # Generate new background
        background = pygame.Surface(self.screen.get_size())
        background.fill(sky_color)
        
        if clouds:
            cloud_color = (220, 240, 255)
            for cx in (60, 200, 340):
                pygame.draw.circle(background, cloud_color, (cx, 90), 22)
                pygame.draw.circle(background, cloud_color, (cx + 20, 100), 18)
                pygame.draw.circle(background, cloud_color, (cx - 18, 100), 16)
        
        self.background_cache = background
        self.last_background_hash = bg_hash
        return background
    
    def batch_draw_sprites(self, sprites: list) -> None:
        """Batch draw multiple sprites efficiently."""
        if not sprites:
            return
        
        # Group sprites by type for efficient rendering
        sprite_groups = {}
        for sprite in sprites:
            sprite_type = type(sprite).__name__
            if sprite_type not in sprite_groups:
                sprite_groups[sprite_type] = []
            sprite_groups[sprite_type].append(sprite)
        
        # Render each group
        for sprite_type, group in sprite_groups.items():
            for sprite in group:
                sprite.draw(self.screen)


class SpatialHashGrid:
    """Spatial hash grid for efficient collision detection."""
    
    def __init__(self, cell_size: int = 64):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], list] = {}
    
    def clear(self) -> None:
        """Clear the spatial grid."""
        self.grid.clear()
    
    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        return (int(x // self.cell_size), int(y // self.cell_size))
    
    def insert(self, obj: Any, x: float, y: float, width: float, height: float) -> None:
        """Insert object into spatial grid."""
        # Get all cells the object spans
        min_cell = self._get_cell(x, y)
        max_cell = self._get_cell(x + width, y + height)
        
        for cell_x in range(min_cell[0], max_cell[0] + 1):
            for cell_y in range(min_cell[1], max_cell[1] + 1):
                cell = (cell_x, cell_y)
                if cell not in self.grid:
                    self.grid[cell] = []
                self.grid[cell].append(obj)
    
    def query(self, x: float, y: float, width: float, height: float) -> set:
        """Query objects in a region."""
        objects = set()
        
        min_cell = self._get_cell(x, y)
        max_cell = self._get_cell(x + width, y + height)
        
        for cell_x in range(min_cell[0], max_cell[0] + 1):
            for cell_y in range(min_cell[1], max_cell[1] + 1):
                cell = (cell_x, cell_y)
                if cell in self.grid:
                    objects.update(self.grid[cell])
        
        return objects


@lru_cache(maxsize=128)
def get_rotated_surface(surface_id: int, angle: float) -> pygame.Surface:
    """Cache rotated surfaces to avoid repeated rotation calculations."""
    # This would need to be implemented with actual surface storage
    # For now, it's a placeholder for the caching concept
    pass


class EfficiencyManager:
    """Main efficiency management system."""
    
    def __init__(self, screen: pygame.Surface, target_fps: int = 60):
        self.monitor = PerformanceMonitor(target_fps)
        self.renderer = OptimizedRenderer(screen)
        self.spatial_grid = SpatialHashGrid()
        
        # Optimization flags
        self.use_dirty_rects = True
        self.use_surface_caching = True
        self.use_spatial_partitioning = True
        self.adaptive_quality = True
    
    def update(self, dt: float, clock: pygame.time.Clock) -> None:
        """Update efficiency systems."""
        self.monitor.update(dt, clock)
        self.monitor.reset_counters()
        self.spatial_grid.clear()
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get comprehensive performance information."""
        cache_hits, cache_misses, hit_rate = self.renderer.surface_cache.get_stats()
        
        return {
            "fps": self.monitor.metrics.fps,
            "frame_time_ms": self.monitor.metrics.frame_time * 1000,
            "memory_mb": self.monitor.metrics.memory_usage,
            "cpu_percent": self.monitor.metrics.cpu_usage,
            "quality_level": self.monitor.quality_level,
            "draw_calls": self.monitor.metrics.draw_calls,
            "collision_checks": self.monitor.metrics.collision_checks,
            "cache_hit_rate": hit_rate,
            "cache_size": len(self.renderer.surface_cache.cache)
        }