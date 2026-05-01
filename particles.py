# particles.py — reusable particle system (feature #91)
import pygame
import random
import math
import struct
from typing import List

from settings import WIDTH


class Particle:
    """A single visual particle with position, velocity, colour, and lifetime."""

    __slots__ = ("x", "y", "vx", "vy", "color", "size", "lifetime",
                 "max_lifetime", "gravity", "alive")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: tuple, size: float, lifetime: float,
                 gravity: float = 0.05) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.gravity = gravity
        self.alive = True

    def update(self, dt: float) -> None:
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.gravity * dt * 60
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        alpha = max(0.0, self.lifetime / self.max_lifetime)
        radius = max(1, int(self.size * alpha))
        r, g, b = self.color[:3]
        # Blit a tiny SRCALPHA circle so particles fade smoothly
        diam = radius * 2
        tmp = pygame.Surface((diam, diam), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (r, g, b, int(255 * alpha)), (radius, radius), radius)
        surf.blit(tmp, (int(self.x) - radius, int(self.y) - radius))


class FloatingText:
    """A short text string that rises and fades (used for +1 score pop, #11)."""

    def __init__(self, x: float, y: float, text: str,
                 color: tuple = (255, 255, 255), font_size: int = 28) -> None:
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.font_size = font_size
        self.lifetime = 0.70
        self.max_lifetime = 0.70
        self.vy = -1.2
        self.alive = True

    def update(self, dt: float) -> None:
        self.y += self.vy * dt * 60
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return
        alpha = max(0.0, self.lifetime / self.max_lifetime)
        font = pygame.font.SysFont(None, self.font_size)
        r, g, b = self.color[:3]
        text_surf = font.render(self.text, True, (r, g, b))
        text_surf.set_alpha(int(255 * alpha))
        rect = text_surf.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(text_surf, rect)


class ScreenShake:
    """Manages a decaying screen-shake offset (feature #9)."""

    def __init__(self) -> None:
        self.timer = 0.0
        self.intensity = 0.0

    def trigger(self, duration: float = 0.30, intensity: float = 6.0) -> None:
        self.timer = duration
        self.intensity = intensity

    def update(self, dt: float) -> None:
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)

    @property
    def offset(self) -> tuple:
        if self.timer <= 0:
            return (0, 0)
        factor = self.timer / 0.30
        mag = int(self.intensity * factor)
        if mag < 1:
            return (0, 0)
        return (random.randint(-mag, mag), random.randint(-mag, mag))

    @property
    def active(self) -> bool:
        return self.timer > 0


class ParticleSystem:
    """Manages a heterogeneous pool of Particle and FloatingText objects."""

    def __init__(self) -> None:
        self.particles: List[Particle] = []
        self.texts: List[FloatingText] = []
        self.screen_shake = ScreenShake()

    # ------------------------------------------------------------------
    # Low-level emitters
    # ------------------------------------------------------------------

    def _emit(self, x: float, y: float, count: int,
              colors: List[tuple], speed_lo: float, speed_hi: float,
              size_lo: float, size_hi: float,
              life_lo: float, life_hi: float,
              angle_lo: float = 0, angle_hi: float = 360,
              gravity: float = 0.05) -> None:
        for _ in range(count):
            angle = math.radians(random.uniform(angle_lo, angle_hi))
            spd = random.uniform(speed_lo, speed_hi)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * spd, math.sin(angle) * spd,
                random.choice(colors),
                random.uniform(size_lo, size_hi),
                random.uniform(life_lo, life_hi),
                gravity,
            ))

    # ------------------------------------------------------------------
    # Named emitters (one per visual effect)
    # ------------------------------------------------------------------

    def emit_death(self, x: float, y: float) -> None:
        """Feather burst on collision (#10)."""
        self._emit(x, y, 12,
                   [(250, 210, 70), (200, 160, 20), (255, 255, 200), (200, 180, 60)],
                   1.5, 5.5, 3, 7, 0.5, 1.0, gravity=0.12)
        self.screen_shake.trigger(0.30, 6.0)

    def emit_score(self, x: float, y: float) -> None:
        """Star sparkles on score (#18) and +1 pop (#11)."""
        self._emit(x, y, 6,
                   [(255, 220, 50), (255, 255, 150), (255, 180, 30)],
                   0.5, 2.5, 2, 5, 0.35, 0.65, gravity=-0.02)
        self.texts.append(FloatingText(x, y - 20, "+1", (255, 240, 80), 30))

    def emit_best_score(self, width: int) -> None:
        """Gold celebration on new personal best (#12)."""
        colors = [(255, 220, 50), (255, 180, 0), (255, 255, 150), (200, 255, 100)]
        for cx in (width // 4, width // 2, 3 * width // 4):
            self._emit(cx, 120, 10, colors, 1, 3.5, 3, 7, 0.6, 1.3, gravity=-0.05)
        self.texts.append(FloatingText(width // 2, 160, "NEW BEST!", (255, 220, 50), 36))

    def emit_flap(self, x: float, y: float) -> None:
        """Wing puff on flap (#15)."""
        self._emit(x - 8, y + 5, 4,
                   [(255, 255, 255), (220, 230, 255)],
                   0.3, 1.2, 2, 4, 0.18, 0.38,
                   angle_lo=150, angle_hi=220, gravity=-0.01)

    def emit_coin(self, x: float, y: float) -> None:
        """Sparkle on coin collect (#57)."""
        self._emit(x, y, 5,
                   [(255, 215, 0), (255, 255, 100), (200, 180, 20)],
                   0.8, 2.5, 2, 4, 0.25, 0.55, gravity=-0.03)
        self.texts.append(FloatingText(x, y - 15, f"+{1}", (255, 215, 0), 24))

    def emit_powerup(self, x: float, y: float, color: tuple) -> None:
        """Flash on power-up collect."""
        self._emit(x, y, 8, [color, (255, 255, 255)],
                   1, 3, 3, 6, 0.4, 0.8, gravity=-0.02)

    def emit_close_call(self, x: float, y: float) -> None:
        """Tiny red sparks on near miss (#14)."""
        self._emit(x, y, 4,
                   [(255, 80, 80), (255, 150, 100)],
                   0.5, 1.5, 2, 4, 0.2, 0.4, gravity=0.02)

    def emit_life_lost(self, x: float, y: float) -> None:
        """Heart-shaped red burst when a survival life is lost."""
        self._emit(x, y, 8,
                   [(255, 50, 80), (220, 20, 50), (255, 150, 150)],
                   1, 4, 3, 6, 0.4, 0.8, gravity=0.08)
        self.texts.append(FloatingText(x, y - 20, "−1 ♥", (255, 80, 80), 28))

    def emit_life_gain(self, x: float, y: float) -> None:
        """Green burst when a survival life is restored."""
        self._emit(x, y, 6,
                   [(80, 220, 100), (150, 255, 150)],
                   0.5, 2, 2, 5, 0.35, 0.65, gravity=-0.03)
        self.texts.append(FloatingText(x, y - 20, "+1 ♥", (80, 220, 100), 28))

    def emit_stars(self, surf_width: int, surf_height: int, count: int = 2) -> None:
        """Ambient star twinkles for night mode (#43)."""
        for _ in range(count):
            x = random.uniform(0, surf_width)
            y = random.uniform(0, surf_height * 0.6)
            self.particles.append(Particle(
                x, y, 0, 0,
                (255, 255, 220), random.uniform(1, 2.5),
                random.uniform(0.8, 1.8), 0.0,
            ))

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.screen_shake.update(dt)
        for p in self.particles:
            p.update(dt)
        for t in self.texts:
            t.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        self.texts = [t for t in self.texts if t.alive]

    def draw(self, surf: pygame.Surface) -> None:
        for p in self.particles:
            p.draw(surf)
        for t in self.texts:
            t.draw(surf)

    def clear(self) -> None:
        self.particles.clear()
        self.texts.clear()
        self.screen_shake.timer = 0.0
