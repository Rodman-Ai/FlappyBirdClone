# sprites.py — enhanced sprite classes with performance optimizations
import pygame
from pygame import Rect
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict
import random
from functools import lru_cache

from settings import (WIDTH, HEIGHT, FLOOR_HEIGHT, BIRD_RADIUS,
                      PIPE_WIDTH, PIPE_GAP, PIPE_SPEED, GRAVITY, FLAP_VELOCITY)

# Module-level cache state
_cache_enabled: bool = False
_pipe_surface_cache: Dict[Tuple, pygame.Surface] = {}


class OptimizedSprite:
    """Base class providing dirty-flagging and surface caching for game sprites."""

    def __init__(self) -> None:
        self._dirty: bool = True
        self.cached_surface: Optional[pygame.Surface] = None

    def mark_dirty(self) -> None:
        """Mark this sprite as needing redraw, invalidating cached surface."""
        self._dirty = True
        self.cached_surface = None

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False


@dataclass
class PipePair(OptimizedSprite):
    """Optimized pipe pair with surface caching and efficient collision detection.

    Attributes:
        x: Horizontal position of the pipe pair
        gap_y: Vertical center of the gap between pipes
        gap: Size of the gap between top and bottom pipes
        width: Width of the pipes
        speed: Horizontal movement speed
        scored: Whether this pipe has been scored
        active: Whether this pipe is currently in use (for object pooling)
    """
    x: float
    gap_y: int
    gap: int = PIPE_GAP
    width: int = PIPE_WIDTH
    speed: float = PIPE_SPEED
    scored: bool = False
    active: bool = True

    def __post_init__(self):
        super().__init__()
        self._cached_rects: Optional[Tuple[Rect, Rect]] = None
        self._last_rect_x: Optional[float] = None

    def rects(self) -> Tuple[Rect, Rect]:
        """Return cached collision rectangles, recomputing only when position changed."""
        if (self._cached_rects is not None and
                self._last_rect_x is not None and
                abs(self.x - self._last_rect_x) < 1.0):
            return self._cached_rects

        top_height = max(0, int(self.gap_y - self.gap // 2))
        bottom_y = int(self.gap_y + self.gap // 2)
        bottom_height = max(0, int((HEIGHT - FLOOR_HEIGHT) - bottom_y))

        top_rect = Rect(int(self.x), 0, self.width, top_height)
        bottom_rect = Rect(int(self.x), bottom_y, self.width, bottom_height)

        self._cached_rects = (top_rect, bottom_rect)
        self._last_rect_x = self.x
        return top_rect, bottom_rect

    def update(self, dt: float) -> None:
        """Move pipe leftward; invalidate rect cache when position changes."""
        old_x = self.x
        self.x -= self.speed * (dt * 60.0)
        if abs(self.x - old_x) > 0.5:
            self.mark_dirty()
            self._cached_rects = None

    def draw(self, surf: pygame.Surface) -> None:
        """Draw pipe pair, using pre-rendered surface cache when enabled."""
        top_rect, bottom_rect = self.rects()

        if _cache_enabled:
            if top_rect.height > 0:
                top_surf = get_cached_pipe_surface(self.width, top_rect.height, True)
                surf.blit(top_surf, (top_rect.x, top_rect.y))
            if bottom_rect.height > 0:
                bot_surf = get_cached_pipe_surface(self.width, bottom_rect.height, False)
                surf.blit(bot_surf, (bottom_rect.x, bottom_rect.y))
        else:
            green = (80, 200, 120)
            dark = (40, 120, 80)
            if top_rect.height > 0:
                pygame.draw.rect(surf, green, top_rect)
                pygame.draw.rect(surf, dark, top_rect, 3)
            if bottom_rect.height > 0:
                pygame.draw.rect(surf, green, bottom_rect)
                pygame.draw.rect(surf, dark, bottom_rect, 3)

    def reset(self, x: float, gap_y: int) -> None:
        """Reset pipe for object-pool reuse."""
        self.x = x
        self.gap_y = gap_y
        self.scored = False
        self.active = True
        self.mark_dirty()
        self._cached_rects = None
        self._last_rect_x = None

    def deactivate(self) -> None:
        """Mark pipe inactive; called when returned to object pool."""
        self.active = False
        self._cached_rects = None
        self.cached_surface = None

    @staticmethod
    def random_spawn(x: int) -> "PipePair":
        """Create a new PipePair at a random gap height."""
        return PipePair(x=float(x), gap_y=PipePair.random_gap_y())

    @staticmethod
    def random_gap_y() -> int:
        """Return a random gap-center Y without allocating a throwaway PipePair."""
        min_center = 120
        max_center = HEIGHT - FLOOR_HEIGHT - 120
        return random.randint(min_center, max_center)


class PipePool:
    """Optimized object pool for pipe pairs with lightweight spatial indexing."""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.available: List[PipePair] = []
        self.active: List[PipePair] = []
        self.spatial_grid: dict = {}
        self.grid_size = 100

        for _ in range(pool_size):
            pipe = PipePair(x=0.0, gap_y=HEIGHT // 2)
            pipe.deactivate()
            self.available.append(pipe)

    def get_pipe(self, x: float, gap_y: int) -> PipePair:
        """Retrieve a pipe from the pool (or allocate a new one) and activate it."""
        if self.available:
            pipe = self.available.pop()
            pipe.reset(x, gap_y)
        else:
            pipe = PipePair(x=x, gap_y=gap_y)

        self.active.append(pipe)
        self._add_to_spatial_grid(pipe)
        return pipe

    def return_pipe(self, pipe: PipePair) -> None:
        """Return a pipe to the pool for future reuse."""
        if pipe in self.active:
            self.active.remove(pipe)
            self._remove_from_spatial_grid(pipe)
            pipe.deactivate()
            if len(self.available) < self.pool_size:
                self.available.append(pipe)

    def update_all(self, dt: float) -> List[PipePair]:
        """Update all active pipes; return off-screen pipes to pool."""
        to_remove = []
        for i in range(len(self.active) - 1, -1, -1):
            pipe = self.active[i]
            old_x = pipe.x
            pipe.update(dt)
            if abs(pipe.x - old_x) > self.grid_size / 2:
                self._update_spatial_grid(pipe, old_x)
            if (pipe.x + PIPE_WIDTH) < -50:
                to_remove.append(pipe)
        for pipe in to_remove:
            self.return_pipe(pipe)
        return to_remove

    def get_collision_candidates(self, x: float, y: float, radius: float) -> List[PipePair]:
        """Return only pipes whose X range overlaps the bird's bounding box."""
        bird_left = x - radius
        bird_right = x + radius
        return [
            p for p in self.active
            if not (bird_right < p.x or bird_left > p.x + PIPE_WIDTH)
        ]

    def _add_to_spatial_grid(self, pipe: PipePair) -> None:
        grid_x = int(pipe.x // self.grid_size)
        self.spatial_grid.setdefault(grid_x, []).append(pipe)

    def _remove_from_spatial_grid(self, pipe: PipePair) -> None:
        grid_x = int(pipe.x // self.grid_size)
        cell = self.spatial_grid.get(grid_x)
        if cell and pipe in cell:
            cell.remove(pipe)
            if not cell:
                del self.spatial_grid[grid_x]

    def _update_spatial_grid(self, pipe: PipePair, old_x: float) -> None:
        old_grid_x = int(old_x // self.grid_size)
        new_grid_x = int(pipe.x // self.grid_size)
        if old_grid_x != new_grid_x:
            old_cell = self.spatial_grid.get(old_grid_x)
            if old_cell and pipe in old_cell:
                old_cell.remove(pipe)
                if not old_cell:
                    del self.spatial_grid[old_grid_x]
            self.spatial_grid.setdefault(new_grid_x, []).append(pipe)

    def get_active_pipes(self) -> List[PipePair]:
        return self.active.copy()

    def clear(self) -> None:
        """Return all active pipes to the pool."""
        self.spatial_grid.clear()
        for pipe in self.active[:]:
            self.return_pipe(pipe)


class Bird(OptimizedSprite):
    """Enhanced bird sprite with physics, wing animation, and surface caching."""

    def __init__(self, x: int, y: int, radius: int = BIRD_RADIUS):
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.vel = 0.0
        self.angle = 0.0

        # Physics parameters (mirror of settings constants for per-instance override)
        self.wing_resistance = 0.98
        self.terminal_velocity = 12.0
        self.flap_count = 0
        self.last_flap_time = 0.0

        # Wing animation state
        self.wing_animation = 0.0
        self.flap_animation_speed = 15.0

        # Rotated surface cache keyed by (angle_bucket, wing_phase)
        self.cached_surfaces: dict = {}
        self.last_render_angle: Optional[float] = None
        self.last_position = (float(x), float(y))

    @property
    def rect(self) -> Rect:
        """Bounding rectangle for broad-phase collision checks."""
        return Rect(int(self.x - self.radius), int(self.y - self.radius),
                    self.radius * 2, self.radius * 2)

    def flap(self) -> None:
        """Apply upward impulse and trigger wing animation."""
        self.vel = FLAP_VELOCITY
        self.flap_count += 1
        self.wing_animation = 1.0
        self.y -= 1  # immediate visual nudge

    def update(self, dt: float) -> None:
        """Advance physics by one frame."""
        old_y = self.y
        old_angle = self.angle

        self.vel += GRAVITY * (dt * 60.0)
        if self.vel > 0:
            self.vel *= self.wing_resistance
        self.vel = min(self.vel, self.terminal_velocity)
        self.y += self.vel

        target_angle = max(-35, min(60, -self.vel * 3.5))
        self.angle += (target_angle - self.angle) * 0.2

        if self.wing_animation > 0:
            self.wing_animation = max(0.0, self.wing_animation - self.flap_animation_speed * dt)

        if abs(self.y - old_y) > 0.5 or abs(self.angle - old_angle) > 1.0:
            self.mark_dirty()
            self.last_position = (self.x, old_y)

    def draw(self, surf: pygame.Surface) -> None:
        """Draw bird, using a per-angle surface cache to avoid redundant rotations."""
        angle_key = round(self.angle / 5) * 5
        wing_key = round(self.wing_animation, 1)
        cache_key = (angle_key, wing_key)

        if _cache_enabled and cache_key in self.cached_surfaces:
            rotated = self.cached_surfaces[cache_key]
        else:
            rotated = self._generate_bird_surface()
            if _cache_enabled:
                if len(self.cached_surfaces) > 20:
                    del self.cached_surfaces[next(iter(self.cached_surfaces))]
                self.cached_surfaces[cache_key] = rotated

        surf.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))

    def _generate_bird_surface(self) -> pygame.Surface:
        """Render bird body, eye, beak, and wing onto an SRCALPHA surface, then rotate."""
        size = self.radius * 2 + 10
        body = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        # Body
        pygame.draw.circle(body, (250, 210, 70), (cx, cy), self.radius)
        pygame.draw.circle(body, (200, 160, 20), (cx, cy), self.radius, 2)

        # Wing
        wo = int(self.wing_animation * 3)
        wc = (220, 180, 40) if self.wing_animation > 0.5 else (200, 160, 30)
        ww = self.radius - 2 + wo
        wh = max(3, self.radius // 2 - wo)
        pygame.draw.ellipse(body, wc, pygame.Rect(cx - ww // 2, cy - 2, ww, wh))

        # Eye
        ex, ey = cx + 6, cy - 5
        pygame.draw.circle(body, (255, 255, 255), (ex, ey), 6)
        pygame.draw.circle(body, (0, 0, 0), (ex + 1, ey), 3)
        pygame.draw.circle(body, (255, 255, 255), (ex + 2, ey - 1), 1)

        # Beak
        bp = [(cx + 10, cy - 1), (cx + 18, cy + 2), (cx + 10, cy + 5)]
        pygame.draw.polygon(body, (240, 150, 0), bp)
        pygame.draw.polygon(body, (200, 120, 0), bp, 1)

        return pygame.transform.rotate(body, self.angle)

    def get_flap_count(self) -> int:
        return self.flap_count

    def reset(self, x: int, y: int) -> None:
        """Return bird to initial state, clearing all caches."""
        self.x = float(x)
        self.y = float(y)
        self.vel = 0.0
        self.angle = 0.0
        self.flap_count = 0
        self.wing_animation = 0.0
        self.last_render_angle = None
        self.last_position = (float(x), float(y))
        self.mark_dirty()
        self.cached_surfaces.clear()


# ---------------------------------------------------------------------------
# Pipe surface cache helpers
# ---------------------------------------------------------------------------

def get_cached_pipe_surface(width: int, height: int, is_top: bool) -> pygame.Surface:
    """Return a pre-rendered pipe surface, generating and caching it on first call."""
    if height <= 0:
        s = pygame.Surface((max(1, width), 1))
        return s

    key = (width, height, is_top)
    if key in _pipe_surface_cache:
        return _pipe_surface_cache[key]

    surf = pygame.Surface((width, height))
    green = (80, 200, 120)
    dark = (40, 120, 80)
    mid = (100, 200, 130)

    surf.fill(green)
    # Vertical edge shading
    pygame.draw.line(surf, dark, (0, 0), (0, height - 1), 3)
    pygame.draw.line(surf, dark, (width - 1, 0), (width - 1, height - 1), 3)
    pygame.draw.line(surf, mid, (3, 0), (3, height - 1), 2)

    # Cap facing the gap (bottom of top pipe, top of bottom pipe)
    cap_h = min(14, height)
    overhang = 4
    cap_rect = pygame.Rect(-overhang,
                           height - cap_h if is_top else 0,
                           width + overhang * 2, cap_h)
    pygame.draw.rect(surf, green, cap_rect)
    pygame.draw.rect(surf, dark, cap_rect, 3)

    _pipe_surface_cache[key] = surf
    return surf


def enable_sprite_caching(enabled: bool = True) -> None:
    """Enable or disable global sprite surface caching."""
    global _cache_enabled
    _cache_enabled = enabled


def clear_sprite_cache() -> None:
    """Discard all cached pipe and bird surfaces."""
    global _pipe_surface_cache
    _pipe_surface_cache.clear()


# ---------------------------------------------------------------------------
# Collision helpers
# ---------------------------------------------------------------------------

def circle_rect_collision(cx: float, cy: float, radius: float, rect: Rect) -> bool:
    """Exact circle-vs-AABB test, with fast AABB pre-rejection."""
    if (cx + radius < rect.left or cx - radius > rect.right or
            cy + radius < rect.top or cy - radius > rect.bottom):
        return False
    closest_x = max(rect.left, min(cx, rect.right))
    closest_y = max(rect.top, min(cy, rect.bottom))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx * dx + dy * dy) <= (radius * radius)


def fast_collision_check(bird_x: float, bird_y: float, bird_radius: float,
                         pipes: List[PipePair]) -> bool:
    """Return True if the bird overlaps any pipe in the candidate list."""
    bird_left = bird_x - bird_radius
    bird_right = bird_x + bird_radius
    for pipe in pipes:
        if bird_right >= pipe.x and bird_left <= pipe.x + PIPE_WIDTH:
            top_rect, bottom_rect = pipe.rects()
            if (circle_rect_collision(bird_x, bird_y, bird_radius, top_rect) or
                    circle_rect_collision(bird_x, bird_y, bird_radius, bottom_rect)):
                return True
    return False


def is_perfect_pass(bird_y: float, gap_center_y: float, gap_size: float) -> bool:
    """True when the bird passes through the central 30 % of the gap."""
    center_zone = gap_size * 0.3
    return abs(bird_y - gap_center_y) <= (center_zone / 2)


def is_close_call(bird_y: float, bird_radius: float,
                  gap_center_y: float, gap_size: float) -> bool:
    """True when the bird clears a pipe edge by fewer than 20 px."""
    danger_zone = 20
    gap_half = gap_size / 2
    dist_to_top = abs((gap_center_y - gap_half) - (bird_y + bird_radius))
    dist_to_bottom = abs((gap_center_y + gap_half) - (bird_y - bird_radius))
    return min(dist_to_top, dist_to_bottom) <= danger_zone
