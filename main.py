# main.py — Enhanced Flappy Bird with comprehensive performance optimizations
"""Ultra-optimized Flappy Bird clone with advanced performance features.

Run on desktop:
    python main.py

Build for web/mobile (requires pygbag):
    python -m pygbag main.py
"""
import asyncio
import pygame
import sys
import time
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, K_SPACE, K_r, K_p, K_F1,
                            MOUSEBUTTONDOWN, USEREVENT)
from typing import List

from settings import (
    WIDTH, HEIGHT, FPS, FLOOR_HEIGHT, BIRD_X, BIRD_RADIUS, SPAWN_MS, PIPE_WIDTH,
    SKY_COLOR, FLOOR_COLOR, FLOOR_BORDER_COLOR, PIPE_POOL_SIZE,
)
from sprites import (
    Bird, PipePair, PipePool, fast_collision_check,
    is_perfect_pass, is_close_call, enable_sprite_caching, clear_sprite_cache,
)
from game_stats import GameStatistics, AchievementManager, GameConfig
from performance import EfficiencyManager


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _generate_floor_surface(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height))
    surface.fill(FLOOR_COLOR)
    pygame.draw.line(surface, FLOOR_BORDER_COLOR, (0, 0), (width, 0), 3)
    return surface


def draw_floor(surf: pygame.Surface, renderer) -> None:
    try:
        floor = renderer.get_cached_surface("floor", _generate_floor_surface,
                                            WIDTH, FLOOR_HEIGHT)
        surf.blit(floor, (0, HEIGHT - FLOOR_HEIGHT))
    except pygame.error:
        pass


def render_text_center(surf: pygame.Surface, text: str, y: int,
                       small: bool = False) -> None:
    """Render white text with a drop shadow, horizontally centred."""
    font = pygame.font.SysFont(None, 28 if small else 42)
    shadow = font.render(text, True, (0, 0, 0))
    label = font.render(text, True, (255, 255, 255))
    rect = label.get_rect(center=(WIDTH // 2, y))
    surf.blit(shadow, shadow.get_rect(center=(WIDTH // 2 + 2, y + 2)))
    surf.blit(label, rect)


def draw_achievement_notification(surf: pygame.Surface, notifications: List,
                                  display_time: float) -> None:
    """Show the most recently unlocked achievement name at the bottom of the screen."""
    if not notifications or display_time <= 0:
        return
    latest = notifications[-1]
    panel = pygame.Surface((WIDTH - 40, 44), pygame.SRCALPHA)
    alpha = min(200, int(display_time * 150))
    panel.fill((0, 0, 0, alpha))
    surf.blit(panel, (20, HEIGHT - 110))
    render_text_center(surf, f"Unlocked: {latest.name}!", HEIGHT - 95, small=True)


def draw_performance_overlay(surf: pygame.Surface, efficiency_manager) -> None:
    """Render a semi-transparent performance metrics panel (toggled with F1)."""
    info = efficiency_manager.get_performance_info()
    font = pygame.font.SysFont(None, 20)
    lines = [
        f"FPS: {info['fps']:.1f}",
        f"Frame: {info['frame_time_ms']:.1f} ms",
        f"Mem: {info['memory_mb']:.1f} MB",
        f"CPU: {info['cpu_percent']:.1f}%",
        f"Quality: {info['quality_level']:.2f}",
        f"Cache hit: {info['cache_hit_rate']:.0f}%",
        f"Draw calls: {info['draw_calls']}",
    ]
    panel = pygame.Surface((148, len(lines) * 18 + 10), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    surf.blit(panel, (5, 30))
    for i, line in enumerate(lines):
        surf.blit(font.render(line, True, (80, 255, 80)), (10, 35 + i * 18))


# ---------------------------------------------------------------------------
# Main game loop (async for pygbag web/mobile compatibility)
# ---------------------------------------------------------------------------

async def main() -> None:
    """Main game loop."""
    pygame.init()
    pygame.display.set_caption("Flappy Bird")

    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
    except pygame.error as e:
        print(f"Failed to create display: {e}")
        return

    clock = pygame.time.Clock()

    efficiency_manager = EfficiencyManager(screen, FPS)
    performance_monitor = efficiency_manager.monitor

    enable_sprite_caching(True)

    config = GameConfig()
    stats = GameStatistics()
    achievement_manager = AchievementManager()

    # Game state machine: READY -> PLAYING -> PAUSED -> GAMEOVER -> READY
    state = "READY"
    score = 0
    game_start_time = 0.0
    current_flaps = 0
    show_performance = config.get("show_performance", False)

    achievement_notifications: List = []
    notification_display_time = 0.0

    bird = Bird(BIRD_X, HEIGHT // 2, BIRD_RADIUS)
    pipe_pool = PipePool(PIPE_POOL_SIZE)

    SPAWN_EVENT = USEREVENT + 1
    pygame.time.set_timer(SPAWN_EVENT, SPAWN_MS)

    def _do_flap() -> None:
        nonlocal current_flaps
        bird.flap()
        current_flaps += 1

    def _start_game() -> None:
        nonlocal state, game_start_time, current_flaps
        state = "PLAYING"
        game_start_time = time.time()
        _do_flap()
        current_flaps = 1  # reset after flap so first flap counts as 1

    def _restart_game() -> None:
        nonlocal state, score, current_flaps, notification_display_time
        state = "READY"
        score = 0
        current_flaps = 0
        notification_display_time = 0.0
        bird.reset(BIRD_X, HEIGHT // 2)
        pipe_pool.clear()
        achievement_notifications.clear()
        clear_sprite_cache()

    def _end_game() -> None:
        nonlocal state, notification_display_time
        state = "GAMEOVER"
        game_time = time.time() - game_start_time
        stats.update_game_end(score, score, current_flaps, game_time)
        new_ach = achievement_manager.check_achievements(
            stats, score, current_flaps, game_time)
        if new_ach:
            achievement_notifications.extend(new_ach)
            notification_display_time = 2.5

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        efficiency_manager.update(dt, clock)
        performance_monitor.increment_draw_calls()

        if notification_display_time > 0:
            notification_display_time -= dt

        # ---- Event handling ----
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    if state == "READY":
                        _start_game()
                    elif state == "PLAYING":
                        _do_flap()
                elif event.key == K_r and state == "GAMEOVER":
                    _restart_game()
                elif event.key == K_p:
                    if state == "PLAYING":
                        state = "PAUSED"
                    elif state == "PAUSED":
                        state = "PLAYING"
                elif event.key == K_F1:
                    show_performance = not show_performance
                    config.set("show_performance", show_performance)

            # Mouse click and touch tap share the same action map
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if state == "READY":
                    _start_game()
                elif state == "PLAYING":
                    _do_flap()
                elif state == "GAMEOVER":
                    _restart_game()
                elif state == "PAUSED":
                    state = "PLAYING"

            elif event.type == pygame.FINGERDOWN:
                if state == "READY":
                    _start_game()
                elif state == "PLAYING":
                    _do_flap()
                elif state == "GAMEOVER":
                    _restart_game()
                elif state == "PAUSED":
                    state = "PLAYING"

            elif event.type == SPAWN_EVENT and state == "PLAYING":
                pipe_pool.get_pipe(WIDTH + 16, PipePair.random_gap_y())

        # ---- Update ----
        if state == "PLAYING":
            bird.update(dt)
            pipe_pool.update_all(dt)

            for pipe in pipe_pool.get_active_pipes():
                if not pipe.scored and (pipe.x + PIPE_WIDTH) < BIRD_X:
                    score += 1
                    pipe.scored = True
                    if is_perfect_pass(bird.y, pipe.gap_y, pipe.gap):
                        stats.perfect_passes += 1
                    if is_close_call(bird.y, bird.radius, pipe.gap_y, pipe.gap):
                        stats.close_calls += 1

            # Boundary collision
            if (bird.y + bird.radius >= HEIGHT - FLOOR_HEIGHT or
                    bird.y - bird.radius <= 0):
                _end_game()
            else:
                candidates = pipe_pool.get_collision_candidates(
                    bird.x, bird.y, bird.radius)
                performance_monitor.increment_collision_checks()
                if fast_collision_check(bird.x, bird.y, bird.radius, candidates):
                    _end_game()

        # ---- Render ----
        try:
            bg = efficiency_manager.renderer.render_background_cached(
                SKY_COLOR, not performance_monitor.should_skip_effects())
            screen.blit(bg, (0, 0))

            active_pipes = pipe_pool.get_active_pipes()
            if active_pipes:
                efficiency_manager.renderer.batch_draw_sprites(active_pipes)

            draw_floor(screen, efficiency_manager.renderer)
            bird.draw(screen)

            if state == "READY":
                render_text_center(screen, "Tap or Space to Flap", HEIGHT // 2 - 80)
                render_text_center(screen, "Pass pipes to score",
                                   HEIGHT // 2 - 35, small=True)
                render_text_center(screen, "P = pause   F1 = perf stats",
                                   HEIGHT // 2 + 10, small=True)
            elif state == "PLAYING":
                render_text_center(screen, str(score), 70)
                if config.get("show_fps", False) and not performance_monitor.should_skip_effects():
                    font = pygame.font.SysFont(None, 24)
                    screen.blit(font.render(f"FPS: {int(clock.get_fps())}", True,
                                            (255, 255, 255)), (10, 10))
            elif state == "PAUSED":
                render_text_center(screen, "PAUSED", HEIGHT // 2 - 40)
                render_text_center(screen, "Tap or P to resume",
                                   HEIGHT // 2 + 10, small=True)
            elif state == "GAMEOVER":
                render_text_center(screen, "Game Over", HEIGHT // 2 - 70)
                render_text_center(screen, f"Score: {score}", HEIGHT // 2 - 30)
                if stats.best_score > 0:
                    render_text_center(screen, f"Best: {stats.best_score}",
                                       HEIGHT // 2 + 10, small=True)
                render_text_center(screen, "Tap or R to play again",
                                   HEIGHT // 2 + 50, small=True)
                if stats.total_games > 1 and not performance_monitor.should_skip_effects():
                    render_text_center(screen, f"Games played: {stats.total_games}",
                                       HEIGHT // 2 + 85, small=True)

            draw_achievement_notification(
                screen, achievement_notifications, notification_display_time)

            if show_performance:
                draw_performance_overlay(screen, efficiency_manager)

            pygame.display.flip()

        except pygame.error as e:
            print(f"Rendering error: {e}")

        # Yield to the browser event loop (required by pygbag; harmless on desktop)
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
