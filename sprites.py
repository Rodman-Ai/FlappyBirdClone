# sprites.py — enhanced sprite classes with performance optimizations
import pygame
from pygame import Rect
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
import random
import math

from settings import (
    WIDTH, HEIGHT, FLOOR_HEIGHT, BIRD_RADIUS, PIPE_WIDTH, PIPE_GAP,
    PIPE_SPEED, GRAVITY, FLAP_VELOCITY, BIRD_SKINS,
    POWERUP_RADIUS, POWERUP_COLORS, POWERUP_LABELS,
    COIN_RADIUS, MOVING_PIPE_AMPLITUDE, MOVING_PIPE_FREQ,
    SURFACE_CACHE_MAX,
)

# ---------------------------------------------------------------------------
# Module-level cache state
# ---------------------------------------------------------------------------
_cache_enabled: bool = False
_pipe_surface_cache: Dict[Tuple, pygame.Surface] = {}


# ---------------------------------------------------------------------------
# OptimizedSprite base (dirty-flag + surface cache)
# ---------------------------------------------------------------------------

class OptimizedSprite:
    """Base class providing dirty-flagging and surface caching for game sprites."""

    def __init__(self) -> None:
        self._dirty: bool = True
        self.cached_surface: Optional[pygame.Surface] = None

    def mark_dirty(self) -> None:
        self._dirty = True
        self.cached_surface = None

    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False


# ---------------------------------------------------------------------------
# PipePair (with optional vertical movement, pipe variants, themes)
# ---------------------------------------------------------------------------

@dataclass
class PipePair(OptimizedSprite):
    """Optimized pipe pair with surface caching and efficient collision detection."""
    x: float
    gap_y: int
    gap: int = PIPE_GAP
    width: int = PIPE_WIDTH
    speed: float = PIPE_SPEED
    scored: bool = False
    active: bool = True
    # Variant (#31-32): "normal" | "wide" | "narrow"
    variant: str = "normal"
    # Moving pipe (#33): True in CHALLENGE / explicit mode
    moving: bool = False
    _move_phase: float = field(default=0.0, repr=False)
    _base_gap_y: int = field(default=0, repr=False)
    # Pipe theme (cosmetic)
    theme: str = "classic"

    def __post_init__(self) -> None:
        super().__init__()
        self._cached_rects: Optional[Tuple[Rect, Rect]] = None
        self._last_rect_x: Optional[float] = None
        self._base_gap_y = self.gap_y

    def rects(self) -> Tuple[Rect, Rect]:
        if (self._cached_rects is not None and
                self._last_rect_x is not None and
                abs(self.x - self._last_rect_x) < 1.0 and not self.moving):
            return self._cached_rects

        top_h = max(0, int(self.gap_y - self.gap // 2))
        bottom_y = int(self.gap_y + self.gap // 2)
        bottom_h = max(0, int((HEIGHT - FLOOR_HEIGHT) - bottom_y))

        self._cached_rects = (
            Rect(int(self.x), 0, self.width, top_h),
            Rect(int(self.x), bottom_y, self.width, bottom_h),
        )
        self._last_rect_x = self.x
        return self._cached_rects

    def update(self, dt: float) -> None:
        old_x = self.x
        self.x -= self.speed * (dt * 60.0)

        if self.moving:
            self._move_phase += MOVING_PIPE_FREQ * 2 * math.pi * dt
            self.gap_y = int(self._base_gap_y +
                             MOVING_PIPE_AMPLITUDE * math.sin(self._move_phase))

        if abs(self.x - old_x) > 0.5 or self.moving:
            self.mark_dirty()
            self._cached_rects = None

    def draw(self, surf: pygame.Surface) -> None:
        top_rect, bottom_rect = self.rects()

        if _cache_enabled:
            if top_rect.height > 0:
                ts = get_cached_pipe_surface(self.width, top_rect.height, True, self.theme)
                surf.blit(ts, (top_rect.x, top_rect.y))
            if bottom_rect.height > 0:
                bs = get_cached_pipe_surface(self.width, bottom_rect.height, False, self.theme)
                surf.blit(bs, (bottom_rect.x, bottom_rect.y))
        else:
            from settings import PIPE_THEMES
            pal = PIPE_THEMES.get(self.theme, PIPE_THEMES["classic"])
            for rect in (top_rect, bottom_rect):
                if rect.height > 0:
                    pygame.draw.rect(surf, pal["fill"], rect)
                    pygame.draw.rect(surf, pal["dark"], rect, 3)

        # Narrow-pipe bonus indicator
        if self.variant == "narrow":
            font = pygame.font.SysFont(None, 18)
            lbl = font.render("+2", True, (255, 220, 50))
            cx = int(self.x + self.width // 2)
            cy = int(self.gap_y)
            surf.blit(lbl, lbl.get_rect(center=(cx, cy)))

    def reset(self, x: float, gap_y: int, theme: str = "classic",
              moving: bool = False, variant: str = "normal",
              gap_override: int = 0) -> None:
        self.x = x
        self.gap_y = gap_y
        self._base_gap_y = gap_y
        self.scored = False
        self.active = True
        self.theme = theme
        self.moving = moving
        self.variant = variant
        self._move_phase = 0.0
        if gap_override:
            self.gap = gap_override
        self.mark_dirty()
        self._cached_rects = None
        self._last_rect_x = None

    def deactivate(self) -> None:
        self.active = False
        self._cached_rects = None
        self.cached_surface = None

    @staticmethod
    def random_gap_y() -> int:
        min_c = 120
        max_c = HEIGHT - FLOOR_HEIGHT - 120
        return random.randint(min_c, max_c)

    @staticmethod
    def random_spawn(x: int) -> "PipePair":
        return PipePair(x=float(x), gap_y=PipePair.random_gap_y())


# ---------------------------------------------------------------------------
# PipePool
# ---------------------------------------------------------------------------

class PipePool:
    """Object pool for PipePair instances with spatial indexing."""

    def __init__(self, pool_size: int = 10) -> None:
        self.pool_size = pool_size
        self.available: List[PipePair] = []
        self.active: List[PipePair] = []
        self.spatial_grid: dict = {}
        self.grid_size = 100

        for _ in range(pool_size):
            p = PipePair(x=0.0, gap_y=HEIGHT // 2)
            p.deactivate()
            self.available.append(p)

    def get_pipe(self, x: float, gap_y: int, theme: str = "classic",
                 moving: bool = False, variant: str = "normal",
                 gap_override: int = 0) -> PipePair:
        if self.available:
            pipe = self.available.pop()
        else:
            pipe = PipePair(x=x, gap_y=gap_y)
        pipe.reset(x, gap_y, theme=theme, moving=moving,
                   variant=variant, gap_override=gap_override)
        self.active.append(pipe)
        self._add_to_grid(pipe)
        return pipe

    def return_pipe(self, pipe: PipePair) -> None:
        if pipe in self.active:
            self.active.remove(pipe)
            self._remove_from_grid(pipe)
            pipe.deactivate()
            if len(self.available) < self.pool_size:
                self.available.append(pipe)

    def update_all(self, dt: float) -> List[PipePair]:
        to_remove = []
        for i in range(len(self.active) - 1, -1, -1):
            pipe = self.active[i]
            old_x = pipe.x
            pipe.update(dt)
            if abs(pipe.x - old_x) > self.grid_size / 2:
                self._update_grid(pipe, old_x)
            if (pipe.x + PIPE_WIDTH) < -50:
                to_remove.append(pipe)
        for pipe in to_remove:
            self.return_pipe(pipe)
        return to_remove

    def get_collision_candidates(self, x: float, y: float, r: float) -> List[PipePair]:
        bl, br = x - r, x + r
        return [p for p in self.active
                if not (br < p.x or bl > p.x + PIPE_WIDTH)]

    def get_active_pipes(self) -> List[PipePair]:
        return self.active.copy()

    def clear(self) -> None:
        self.spatial_grid.clear()
        for p in self.active[:]:
            self.return_pipe(p)

    # ------ spatial grid helpers ------
    def _add_to_grid(self, pipe: PipePair) -> None:
        gx = int(pipe.x // self.grid_size)
        self.spatial_grid.setdefault(gx, []).append(pipe)

    def _remove_from_grid(self, pipe: PipePair) -> None:
        gx = int(pipe.x // self.grid_size)
        cell = self.spatial_grid.get(gx)
        if cell and pipe in cell:
            cell.remove(pipe)
            if not cell:
                del self.spatial_grid[gx]

    def _update_grid(self, pipe: PipePair, old_x: float) -> None:
        og = int(old_x // self.grid_size)
        ng = int(pipe.x // self.grid_size)
        if og != ng:
            old_cell = self.spatial_grid.get(og)
            if old_cell and pipe in old_cell:
                old_cell.remove(pipe)
                if not old_cell:
                    del self.spatial_grid[og]
            self.spatial_grid.setdefault(ng, []).append(pipe)


# ---------------------------------------------------------------------------
# Bird (with skin support)
# ---------------------------------------------------------------------------

class Bird(OptimizedSprite):
    """Enhanced bird sprite with physics, wing animation, and surface caching."""

    def __init__(self, x: int, y: int, radius: int = BIRD_RADIUS,
                 skin: str = "classic") -> None:
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.skin = skin
        self.vel = 0.0
        self.angle = 0.0

        self.wing_resistance = 0.98
        self.terminal_velocity = 12.0
        self.flap_count = 0
        self.last_flap_time = 0.0

        self.wing_animation = 0.0
        self.flap_animation_speed = 15.0

        self.cached_surfaces: Dict[tuple, pygame.Surface] = {}
        self.last_render_angle: Optional[float] = None
        self.last_position = (float(x), float(y))

    @property
    def rect(self) -> Rect:
        return Rect(int(self.x - self.radius), int(self.y - self.radius),
                    self.radius * 2, self.radius * 2)

    def flap(self) -> None:
        self.vel = FLAP_VELOCITY
        self.flap_count += 1
        self.wing_animation = 1.0
        self.y -= 1

    def update(self, dt: float) -> None:
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

    def draw(self, surf: pygame.Surface, alpha: int = 255) -> None:
        ak = round(self.angle / 5) * 5
        wk = round(self.wing_animation, 1)
        cache_key = (ak, wk, self.skin, self.radius)

        if _cache_enabled and cache_key in self.cached_surfaces:
            rot = self.cached_surfaces[cache_key]
        else:
            rot = self._generate_bird_surface()
            if _cache_enabled:
                if len(self.cached_surfaces) > 24:
                    del self.cached_surfaces[next(iter(self.cached_surfaces))]
                self.cached_surfaces[cache_key] = rot

        if alpha < 255:
            rot = rot.copy()
            rot.set_alpha(alpha)
        surf.blit(rot, rot.get_rect(center=(int(self.x), int(self.y))))

    def _generate_bird_surface(self) -> pygame.Surface:
        pal = BIRD_SKINS.get(self.skin, BIRD_SKINS["classic"])
        size = self.radius * 2 + 10
        body = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        pygame.draw.circle(body, pal["body"], (cx, cy), self.radius)
        pygame.draw.circle(body, pal["outline"], (cx, cy), self.radius, 2)

        wo = int(self.wing_animation * 3)
        wc = tuple(max(0, c - 20) for c in pal["wing"])
        if self.wing_animation > 0.5:
            wc = pal["wing"]
        ww = self.radius - 2 + wo
        wh = max(3, self.radius // 2 - wo)
        pygame.draw.ellipse(body, wc, pygame.Rect(cx - ww // 2, cy - 2, ww, wh))

        ex, ey = cx + 6, cy - 5
        pygame.draw.circle(body, pal["eye_bg"], (ex, ey), 6)
        pygame.draw.circle(body, pal["pupil"], (ex + 1, ey), 3)
        pygame.draw.circle(body, (255, 255, 255), (ex + 2, ey - 1), 1)

        bp = [(cx + 10, cy - 1), (cx + 18, cy + 2), (cx + 10, cy + 5)]
        pygame.draw.polygon(body, pal["beak"], bp)
        pygame.draw.polygon(body, tuple(max(0, c - 40) for c in pal["beak"]), bp, 1)

        return pygame.transform.rotate(body, self.angle)

    def get_flap_count(self) -> int:
        return self.flap_count

    def reset(self, x: int, y: int, skin: Optional[str] = None) -> None:
        self.x = float(x)
        self.y = float(y)
        self.vel = 0.0
        self.angle = 0.0
        self.flap_count = 0
        self.wing_animation = 0.0
        self.last_render_angle = None
        self.last_position = (float(x), float(y))
        if skin is not None:
            self.skin = skin
        self.mark_dirty()
        self.cached_surfaces.clear()


# ---------------------------------------------------------------------------
# GhostBird — replays the best run as a transparent overlay (feature #95)
# ---------------------------------------------------------------------------

class GhostBird:
    """Replays recorded (y, angle) frames as a semi-transparent ghost bird."""

    def __init__(self, frames: List[Tuple[float, float]], x: float,
                 radius: int = BIRD_RADIUS) -> None:
        self.frames = frames
        self.frame_idx = 0
        self.x = x
        self.radius = radius
        self.y = frames[0][0] if frames else HEIGHT // 2
        self.angle = frames[0][1] if frames else 0.0
        self._surf_cache: Dict[int, pygame.Surface] = {}

    def update(self) -> None:
        if self.frame_idx < len(self.frames) - 1:
            self.frame_idx += 1
            self.y, self.angle = self.frames[self.frame_idx]

    def draw(self, surf: pygame.Surface) -> None:
        if not self.frames:
            return
        pal = BIRD_SKINS["ghost"]
        size = self.radius * 2 + 10
        body = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2
        pygame.draw.circle(body, (*pal["body"], 120), (cx, cy), self.radius)
        pygame.draw.circle(body, (*pal["outline"], 80), (cx, cy), self.radius, 2)
        rotated = pygame.transform.rotate(body, self.angle)
        surf.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))


# ---------------------------------------------------------------------------
# Coin (feature #57)
# ---------------------------------------------------------------------------

class Coin:
    """Collectible coin that floats in the pipe gap."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.radius = COIN_RADIUS
        self.active = True
        self._phase = random.uniform(0, math.pi * 2)

    def update(self, dt: float, pipe_speed: float) -> None:
        self.x -= pipe_speed * (dt * 60.0)
        self._phase += 3.0 * dt

    def draw(self, surf: pygame.Surface) -> None:
        if not self.active:
            return
        bob = int(math.sin(self._phase) * 3)
        cx, cy = int(self.x), int(self.y) + bob
        # Outer gold ring
        pygame.draw.circle(surf, (255, 215, 0), (cx, cy), self.radius)
        pygame.draw.circle(surf, (200, 160, 0), (cx, cy), self.radius, 2)
        # Inner highlight
        pygame.draw.circle(surf, (255, 240, 120),
                           (cx - self.radius // 3, cy - self.radius // 3),
                           self.radius // 3)

    def collect_check(self, bx: float, by: float, br: float) -> bool:
        dx = self.x - bx
        dy = self.y - by
        return math.sqrt(dx * dx + dy * dy) < (self.radius + br)

    @property
    def off_screen(self) -> bool:
        return self.x + self.radius < -10


# ---------------------------------------------------------------------------
# PowerUpItem (features #53-56)
# ---------------------------------------------------------------------------

class PowerUpItem:
    """A floating power-up icon that appears between pipes."""

    def __init__(self, x: float, y: float, ptype: str) -> None:
        self.x = x
        self.y = y
        self.ptype = ptype
        self.radius = POWERUP_RADIUS
        self.active = True
        self._phase = random.uniform(0, math.pi * 2)

    def update(self, dt: float, pipe_speed: float) -> None:
        self.x -= pipe_speed * (dt * 60.0)
        self._phase += 2.5 * dt

    def draw(self, surf: pygame.Surface) -> None:
        if not self.active:
            return
        bob = int(math.sin(self._phase) * 4)
        cx, cy = int(self.x), int(self.y) + bob
        color = POWERUP_COLORS.get(self.ptype, (200, 200, 200))

        # Glow ring
        glow = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 40),
                           (self.radius * 2, self.radius * 2), self.radius * 2)
        surf.blit(glow, (cx - self.radius * 2, cy - self.radius * 2))

        pygame.draw.circle(surf, color, (cx, cy), self.radius)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), self.radius, 2)

        font = pygame.font.SysFont(None, 18)
        lbl = font.render(POWERUP_LABELS.get(self.ptype, "?"), True, (255, 255, 255))
        surf.blit(lbl, lbl.get_rect(center=(cx, cy)))

    def collect_check(self, bx: float, by: float, br: float) -> bool:
        dx = self.x - bx
        dy = self.y - by
        return math.sqrt(dx * dx + dy * dy) < (self.radius + br)

    @property
    def off_screen(self) -> bool:
        return self.x + self.radius < -10


# ---------------------------------------------------------------------------
# Pipe surface cache helpers
# ---------------------------------------------------------------------------

def get_cached_pipe_surface(width: int, height: int, is_top: bool,
                             theme: str = "classic") -> pygame.Surface:
    """Return a pre-rendered pipe surface, generating and caching on first call."""
    if height <= 0:
        return pygame.Surface((max(1, width), 1))

    key = (width, height, is_top, theme)
    if key in _pipe_surface_cache:
        return _pipe_surface_cache[key]

    # Evict LRU 25% if cache is too large (#90)
    if len(_pipe_surface_cache) >= SURFACE_CACHE_MAX:
        evict = len(_pipe_surface_cache) // 4
        for k in list(_pipe_surface_cache.keys())[:evict]:
            del _pipe_surface_cache[k]

    from settings import PIPE_THEMES
    pal = PIPE_THEMES.get(theme, PIPE_THEMES["classic"])
    fill, dark, mid = pal["fill"], pal["dark"], pal["mid"]

    surf = pygame.Surface((width, height))
    surf.fill(fill)
    pygame.draw.line(surf, dark, (0, 0), (0, height - 1), 3)
    pygame.draw.line(surf, dark, (width - 1, 0), (width - 1, height - 1), 3)
    pygame.draw.line(surf, mid,  (3, 0), (3, height - 1), 2)

    cap_h = min(14, height)
    ov = 4
    cap_rect = pygame.Rect(-ov, height - cap_h if is_top else 0,
                            width + ov * 2, cap_h)
    pygame.draw.rect(surf, fill, cap_rect)
    pygame.draw.rect(surf, dark, cap_rect, 3)

    _pipe_surface_cache[key] = surf
    return surf


def enable_sprite_caching(enabled: bool = True) -> None:
    global _cache_enabled
    _cache_enabled = enabled


def clear_sprite_cache() -> None:
    global _pipe_surface_cache
    _pipe_surface_cache.clear()


# ---------------------------------------------------------------------------
# Collision helpers
# ---------------------------------------------------------------------------

def circle_rect_collision(cx: float, cy: float, r: float, rect: Rect) -> bool:
    if (cx + r < rect.left or cx - r > rect.right or
            cy + r < rect.top or cy - r > rect.bottom):
        return False
    clx = max(rect.left, min(cx, rect.right))
    cly = max(rect.top, min(cy, rect.bottom))
    dx, dy = cx - clx, cy - cly
    return (dx * dx + dy * dy) <= r * r


def fast_collision_check(bx: float, by: float, br: float,
                         pipes: List[PipePair]) -> bool:
    bl, brr = bx - br, bx + br
    for pipe in pipes:
        if brr >= pipe.x and bl <= pipe.x + PIPE_WIDTH:
            top, bot = pipe.rects()
            if (circle_rect_collision(bx, by, br, top) or
                    circle_rect_collision(bx, by, br, bot)):
                return True
    return False


def is_perfect_pass(bird_y: float, gap_cy: float, gap: float) -> bool:
    return abs(bird_y - gap_cy) <= (gap * 0.3 / 2)


def is_close_call(bird_y: float, bird_r: float, gap_cy: float, gap: float) -> bool:
    gh = gap / 2
    d_top = abs((gap_cy - gh) - (bird_y + bird_r))
    d_bot = abs((gap_cy + gh) - (bird_y - bird_r))
    return min(d_top, d_bot) <= 20
