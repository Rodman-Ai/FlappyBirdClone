# sprites.py — enhanced sprite classes with performance optimizations
import pygame
from pygame import Rect
from dataclasses import dataclass
from typing import Tuple, List, Optional
import random
import math
from functools import lru_cache

from settings import WIDTH, HEIGHT, FLOOR_HEIGHT, BIRD_RADIUS, PIPE_WIDTH, PIPE_GAP, PIPE_SPEED, GRAVITY, FLAP_VELOCITY

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
        self._cached_rects = None
        self._last_rect_x = None

    def rects(self) -> Tuple[Rect, Rect]:
        """Calculate collision rectangles for top and bottom pipes with caching.
        
        Returns:
            Tuple of (top_rect, bottom_rect) for collision detection
        """
        # Cache rectangles if position hasn't changed significantly
        if (self._cached_rects is not None and 
            self._last_rect_x is not None and 
            abs(self.x - self._last_rect_x) < 1.0):
            return self._cached_rects
            
        top_height = max(0, int(self.gap_y - self.gap // 2))
        bottom_y = int(self.gap_y + self.gap // 2)
        bottom_height = max(0, int((HEIGHT - FLOOR_HEIGHT) - bottom_y))
        
        top_rect = Rect(int(self.x), 0, self.width, top_height)
        bottom_rect = Rect(int(self.x), bottom_y, self.width, bottom_height)
        
        # Cache the results
        self._cached_rects = (top_rect, bottom_rect)
        self._last_rect_x = self.x
        
        return top_rect, bottom_rect

    def update(self, dt: float) -> None:
        """Update pipe position with efficient movement tracking.
        
        Args:
            dt: Delta time in seconds
        """
        old_x = self.x
        self.x -= self.speed * (dt * 60.0)
        
        # Mark dirty if position changed significantly
        if abs(self.x - old_x) > 0.5:
            self.mark_dirty()
            self._cached_rects = None  # Invalidate rect cache

    def draw(self, surf: pygame.Surface) -> None:
        """Draw the pipe pair with surface caching optimization.
        
        Args:
            surf: Pygame surface to draw on
        """
        top_rect, bottom_rect = self.rects()
        
        # Use cached surfaces for pipes if available
        if _cache_enabled:
            top_surface = get_cached_pipe_surface(self.width, top_rect.height, True)
            bottom_surface = get_cached_pipe_surface(self.width, bottom_rect.height, False)
            
            surf.blit(top_surface, (top_rect.x, top_rect.y))
            surf.blit(bottom_surface, (bottom_rect.x, bottom_rect.y))
        else:
            # Fallback to direct drawing
            green = (80, 200, 120)
            dark = (40, 120, 80)
            pygame.draw.rect(surf, green, top_rect)
            pygame.draw.rect(surf, dark, top_rect, 3)
            pygame.draw.rect(surf, green, bottom_rect)
            pygame.draw.rect(surf, dark, bottom_rect, 3)
    
    def reset(self, x: float, gap_y: int) -> None:
        """Reset pipe for reuse in object pool with cache invalidation.
        
        Args:
            x: New horizontal position
            gap_y: New gap center position
        """
        self.x = x
        self.gap_y = gap_y
        self.scored = False
        self.active = True
        self.mark_dirty()
        
        # Invalidate caches
        self._cached_rects = None
        self._last_rect_x = None
    
    def deactivate(self) -> None:
        """Mark pipe as inactive for object pooling with cleanup."""
        self.active = False
        self._cached_rects = None
        self.cached_surface = None

    @staticmethod
    def random_spawn(x: int) -> "PipePair":
        """Create a new pipe pair at a random height.
        
        Args:
            x: Horizontal spawn position
            
        Returns:
            New PipePair instance with random gap position
        """
        min_center = 120
        max_center = HEIGHT - FLOOR_HEIGHT - 120
        gap_y = random.randint(min_center, max_center)
        return PipePair(x=float(x), gap_y=gap_y)

class PipePool:
    """Optimized object pool for pipe pairs with spatial indexing."""
    
    def __init__(self, pool_size: int = 10):
        """Initialize the pipe pool with performance optimizations.
        
        Args:
            pool_size: Maximum number of pipes to keep in pool
        """
        self.pool_size = pool_size
        self.available: List[PipePair] = []
        self.active: List[PipePair] = []
        self.spatial_grid: dict = {}  # Simple spatial partitioning
        self.grid_size = 100  # Grid cell size for spatial queries
        
        # Pre-allocate pipe objects
        for _ in range(pool_size):
            pipe = PipePair(x=0, gap_y=HEIGHT//2)
            pipe.deactivate()
            self.available.append(pipe)
    
    def get_pipe(self, x: float, gap_y: int) -> PipePair:
        """Get a pipe from the pool with spatial indexing.
        
        Args:
            x: Horizontal position for the pipe
            gap_y: Gap center position
            
        Returns:
            PipePair ready for use
        """
        if self.available:
            pipe = self.available.pop()
            pipe.reset(x, gap_y)
        else:
            pipe = PipePair(x=x, gap_y=gap_y)
        
        self.active.append(pipe)
        self._add_to_spatial_grid(pipe)
        return pipe
    
    def return_pipe(self, pipe: PipePair) -> None:
        """Return a pipe to the pool with spatial cleanup.
        
        Args:
            pipe: PipePair to return to pool
        """
        if pipe in self.active:
            self.active.remove(pipe)
            self._remove_from_spatial_grid(pipe)
            pipe.deactivate()
            
            # Only keep up to pool_size pipes in available list
            if len(self.available) < self.pool_size:
                self.available.append(pipe)
    
    def update_all(self, dt: float) -> List[PipePair]:
        """Update all active pipes with optimized iteration.
        
        Args:
            dt: Delta time in seconds
            
        Returns:
            List of pipes that should be removed (off-screen)
        """
        to_remove = []
        
        # Use reverse iteration to avoid index issues when removing
        for i in range(len(self.active) - 1, -1, -1):
            pipe = self.active[i]
            old_x = pipe.x
            pipe.update(dt)
            
            # Update spatial grid if pipe moved significantly
            if abs(pipe.x - old_x) > self.grid_size / 2:
                self._update_spatial_grid(pipe, old_x)
            
            # Mark pipes that are off-screen for removal
            if (pipe.x + PIPE_WIDTH) < -50:
                to_remove.append(pipe)
        
        # Return removed pipes to pool
        for pipe in to_remove:
            self.return_pipe(pipe)
        
        return to_remove
    
    def get_collision_candidates(self, x: float, y: float, radius: float) -> List[PipePair]:
        """Get pipes that could potentially collide with given circle.
        
        Args:
            x: Circle center X
            y: Circle center Y
            radius: Circle radius
            
        Returns:
            List of pipes in collision range
        """
        candidates = []
        
        # Simple optimization: only check pipes near the bird's X position
        bird_left = x - radius
        bird_right = x + radius
        
        for pipe in self.active:
            pipe_left = pipe.x
            pipe_right = pipe.x + PIPE_WIDTH
            
            # Quick AABB check for horizontal overlap
            if not (bird_right < pipe_left or bird_left > pipe_right):
                candidates.append(pipe)
        
        return candidates
    
    def _add_to_spatial_grid(self, pipe: PipePair) -> None:
        """Add pipe to spatial grid for efficient queries."""
        grid_x = int(pipe.x // self.grid_size)
        if grid_x not in self.spatial_grid:
            self.spatial_grid[grid_x] = []
        self.spatial_grid[grid_x].append(pipe)
    
    def _remove_from_spatial_grid(self, pipe: PipePair) -> None:
        """Remove pipe from spatial grid."""
        grid_x = int(pipe.x // self.grid_size)
        if grid_x in self.spatial_grid and pipe in self.spatial_grid[grid_x]:
            self.spatial_grid[grid_x].remove(pipe)
            if not self.spatial_grid[grid_x]:  # Clean up empty cells
                del self.spatial_grid[grid_x]
    
    def _update_spatial_grid(self, pipe: PipePair, old_x: float) -> None:
        """Update pipe position in spatial grid."""
        old_grid_x = int(old_x // self.grid_size)
        new_grid_x = int(pipe.x // self.grid_size)
        
        if old_grid_x != new_grid_x:
            # Remove from old cell
            if old_grid_x in self.spatial_grid and pipe in self.spatial_grid[old_grid_x]:
                self.spatial_grid[old_grid_x].remove(pipe)
                if not self.spatial_grid[old_grid_x]:
                    del self.spatial_grid[old_grid_x]
            
            # Add to new cell
            if new_grid_x not in self.spatial_grid:
                self.spatial_grid[new_grid_x] = []
            self.spatial_grid[new_grid_x].append(pipe)
    def get_active_pipes(self) -> List[PipePair]:
        """Get list of currently active pipes."""
        return self.active.copy()
    
    def clear(self) -> None:
        """Clear all active pipes and return them to pool."""
        self.spatial_grid.clear()
        for pipe in self.active[:]:
            self.return_pipe(pipe)


class Bird(OptimizedSprite):
    """Enhanced bird class with performance optimizations and caching."""
    
    def __init__(self, x: int, y: int, radius: int = BIRD_RADIUS):
        """Initialize the bird with optimization features.
        
        Args:
            x: Initial horizontal position
            y: Initial vertical position
            radius: Bird collision radius
        """
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.vel = 0.0
        self.angle = 0.0  # visual tilt
        
        # Enhanced physics properties
        self.wing_resistance = 0.98  # Air resistance when flapping
        self.terminal_velocity = 12.0  # Maximum fall speed
        self.flap_count = 0
        self.last_flap_time = 0.0
        
        # Visual enhancement with caching
        self.wing_animation = 0.0
        self.flap_animation_speed = 15.0
        self.cached_surfaces: dict = {}  # Cache rotated bird surfaces
        self.last_render_angle = None
    def __init__(self, x: int, y: int, radius: int = BIRD_RADIUS):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.vel = 0.0
        self.angle = 0.0  # visual tilt

    @property
    def rect(self) -> Rect:
        """Get collision rectangle for the bird.
        
        Returns:
            Pygame Rect representing bird's collision area
        """
        return Rect(int(self.x - self.radius), int(self.y - self.radius), 
                   self.radius * 2, self.radius * 2)

    def flap(self) -> None:
        """Make the bird flap with enhanced physics."""
        self.vel = FLAP_VELOCITY
        self.flap_count += 1
        
        # Wing animation
        self.wing_animation = 1.0
        
        # Small upward nudge for immediate feedback
        self.y += -1

    def update(self, dt: float) -> None:
        """Update bird physics with optimized calculations.
        
        Args:
            dt: Delta time in seconds
        """
        old_y = self.y
        old_angle = self.angle
        
        # Apply gravity with realistic acceleration
        gravity_force = GRAVITY * (dt * 60.0)
        self.vel += gravity_force
        
        # Apply wing resistance (air drag) - optimized calculation
        if self.vel > 0:  # Only when falling
            self.vel *= self.wing_resistance
        
        # Terminal velocity limiting
        self.vel = min(self.vel, self.terminal_velocity)
        
        # Update position
        self.y += self.vel
        
        # Enhanced angle calculation with smooth transitions
        target_angle = max(-35, min(60, -self.vel * 3.5))
        self.angle += (target_angle - self.angle) * 0.2  # Smooth transition
        
        # Update wing animation
        if self.wing_animation > 0:
            self.wing_animation -= self.flap_animation_speed * dt
            self.wing_animation = max(0, self.wing_animation)
        
        # Mark dirty if position or angle changed significantly
        if (abs(self.y - old_y) > 0.5 or abs(self.angle - old_angle) > 1.0):
            self.mark_dirty()
            self.last_position = (self.x, old_y)

    def draw(self, surf: pygame.Surface) -> None:
        """Draw enhanced bird with surface caching for rotations.
        
        Args:
            surf: Pygame surface to draw on
        """
        # Check if we can use cached surface
        angle_key = round(self.angle / 5) * 5  # Round to nearest 5 degrees for caching
        wing_key = round(self.wing_animation, 1)
        cache_key = (angle_key, wing_key)
        
        if _cache_enabled and cache_key in self.cached_surfaces:
            rotated_surface = self.cached_surfaces[cache_key]
        else:
            # Generate new surface
            rotated_surface = self._generate_bird_surface()
            if _cache_enabled:
                # Limit cache size
                if len(self.cached_surfaces) > 20:
                    # Remove oldest cache entry
                    oldest_key = next(iter(self.cached_surfaces))
                    del self.cached_surfaces[oldest_key]
                self.cached_surfaces[cache_key] = rotated_surface
        
        # Draw the cached/generated surface
        rect = rotated_surface.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(rotated_surface, rect)
    
    def _generate_bird_surface(self) -> pygame.Surface:
        """Generate bird surface with current animation state."""
        # Create bird surface with alpha for better rendering
        bird_size = self.radius * 2
        body = pygame.Surface((bird_size + 10, bird_size + 10), pygame.SRCALPHA)
        
        center_x, center_y = (bird_size + 10) // 2, (bird_size + 10) // 2
        
        # Body (main circle)
        pygame.draw.circle(body, (250, 210, 70), (center_x, center_y), self.radius)
        pygame.draw.circle(body, (200, 160, 20), (center_x, center_y), self.radius, 2)  # Outline
        
        # Wing animation - optimized calculation
        wing_offset = int(self.wing_animation * 3)
        wing_color = (220, 180, 40) if self.wing_animation > 0.5 else (200, 160, 30)
        
        # Wings (ellipses that change based on animation)
        wing_width = self.radius - 2 + wing_offset
        wing_height = max(3, self.radius // 2 - wing_offset)
        wing_rect = pygame.Rect(center_x - wing_width//2, center_y - 2, wing_width, wing_height)
        pygame.draw.ellipse(body, wing_color, wing_rect)
        
        # Eye (larger and more expressive)
        eye_x = center_x + 6
        eye_y = center_y - 5
        pygame.draw.circle(body, (255, 255, 255), (eye_x, eye_y), 6)
        pygame.draw.circle(body, (0, 0, 0), (eye_x + 1, eye_y), 3)
        pygame.draw.circle(body, (255, 255, 255), (eye_x + 2, eye_y - 1), 1)  # Highlight
        
        # Beak (more detailed)
        beak_points = [
            (center_x + 10, center_y - 1),
            (center_x + 18, center_y + 2),
            (center_x + 10, center_y + 5)
        ]
        pygame.draw.polygon(body, (240, 150, 0), beak_points)
        pygame.draw.polygon(body, (200, 120, 0), beak_points, 1)  # Outline
        
        # Rotate and return
        return pygame.transform.rotate(body, self.angle)
    
    def get_flap_count(self) -> int:
        """Get total number of flaps made."""
        return self.flap_count
    
    def reset(self, x: int, y: int) -> None:
        """Reset bird to initial state with cache cleanup.
        
        Args:
            x: Reset horizontal position
            y: Reset vertical position
        """
        self.x = float(x)
        self.y = float(y)
        self.vel = 0.0
        self.angle = 0.0
        self.flap_count = 0
        self.wing_animation = 0.0
        self.mark_dirty()
        
        # Clear cached surfaces
        self.cached_surfaces.clear()
        self.last_render_angle = None


def circle_rect_collision(cx: float, cy: float, radius: float, rect: Rect) -> bool:
    """Optimized circle-rectangle collision detection.
    
    Args:
        cx: Circle center X coordinate
        cy: Circle center Y coordinate
        radius: Circle radius
        rect: Rectangle to check collision with
        
    Returns:
        True if circle and rectangle collide, False otherwise
    """
    # Quick AABB check first (fastest)
    if (cx + radius < rect.left or cx - radius > rect.right or
        cy + radius < rect.top or cy - radius > rect.bottom):
        return False
    
    # Detailed collision check
    closest_x = max(rect.left, min(cx, rect.right))
    closest_y = max(rect.top, min(cy, rect.bottom))
    dx = cx - closest_x
    dy = cy - closest_y
    return (dx*dx + dy*dy) <= (radius * radius)


def fast_collision_check(bird_x: float, bird_y: float, bird_radius: float, 
                        pipes: List[PipePair]) -> bool:
    """Optimized collision checking with spatial optimization.
    
    Args:
        bird_x: Bird X position
        bird_y: Bird Y position
        bird_radius: Bird collision radius
        pipes: List of pipes to check
        
    Returns:
        True if collision detected
    """
    # Pre-filter pipes by X position (most common case for no collision)
    bird_left = bird_x - bird_radius
    bird_right = bird_x + bird_radius
    
    for pipe in pipes:
        pipe_left = pipe.x
        pipe_right = pipe.x + PIPE_WIDTH
        
        # Quick horizontal overlap check
        if bird_right >= pipe_left and bird_left <= pipe_right:
            # Only do expensive collision check if horizontal overlap exists
            top_rect, bottom_rect = pipe.rects()
            if (circle_rect_collision(bird_x, bird_y, bird_radius, top_rect) or
                circle_rect_collision(bird_x, bird_y, bird_radius, bottom_rect)):
                return True
    
    return False


def is_perfect_pass(bird_y: float, gap_center_y: float, gap_size: float) -> bool:
    """Check if bird passed through center area of pipe gap.
    
    Args:
        bird_y: Bird's Y position
        gap_center_y: Center Y position of pipe gap
        gap_size: Size of the pipe gap
        
    Returns:
        True if bird passed through center third of gap
    """
    center_zone = gap_size * 0.3  # Center 30% of gap
    return abs(bird_y - gap_center_y) <= (center_zone / 2)


def is_close_call(bird_y: float, bird_radius: float, gap_center_y: float, gap_size: float) -> bool:
    """Check if bird had a close call (near collision).
    
    Args:
        bird_y: Bird's Y position
        bird_radius: Bird's collision radius
        gap_center_y: Center Y position of pipe gap
        gap_size: Size of the pipe gap
        
    Returns:
        True if bird was within danger zone but didn't collide
    """
    danger_zone = 20  # Pixels from gap edge to be considered close call
    gap_half = gap_size / 2
    
    # Distance from bird to gap edges
    dist_to_top = abs((gap_center_y - gap_half) - (bird_y + bird_radius))
    dist_to_bottom = abs((gap_center_y + gap_half) - (bird_y - bird_radius))
    
    # Close call if within danger zone of either edge
    return min(dist_to_top, dist_to_bottom) <= danger_zone
