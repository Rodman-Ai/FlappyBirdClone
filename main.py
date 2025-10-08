# main.py — Enhanced Flappy Bird with comprehensive performance optimizations
"""Ultra-optimized Flappy Bird clone with advanced performance features.

This module implements the main game loop with the following optimizations:
- Object pooling for memory optimization
- Surface caching and pre-rendering
- Spatial partitioning for collision detection
- Adaptive quality settings
- Performance monitoring and profiling
- Dirty rectangle updates
"""
import pygame
import sys
import time
from pygame.locals import QUIT, KEYDOWN, K_SPACE, K_r, K_p, K_F1, MOUSEBUTTONDOWN, USEREVENT
from typing import List, Optional

from settings import (
    WIDTH, HEIGHT, FPS, FLOOR_HEIGHT, BIRD_X, BIRD_RADIUS, SPAWN_MS, PIPE_WIDTH,
    SKY_COLOR, FLOOR_COLOR, FLOOR_BORDER_COLOR, CLOUD_COLOR, PIPE_POOL_SIZE
)
from sprites import (
    Bird, PipePair, PipePool, circle_rect_collision, fast_collision_check,
    is_perfect_pass, is_close_call, enable_sprite_caching, clear_sprite_cache
)
from game_stats import GameStatistics, AchievementManager, GameConfig
from performance import EfficiencyManager, PerformanceMonitor

def draw_floor_optimized(surf: pygame.Surface, renderer) -> None:
    """Draw the game floor with caching optimization.
    
    Args:
        surf: Pygame surface to draw on
        renderer: Optimized renderer instance
    """
    try:
        # Use cached floor surface
        floor_surface = renderer.get_cached_surface(
            "floor", _generate_floor_surface, WIDTH, FLOOR_HEIGHT
        )
        surf.blit(floor_surface, (0, HEIGHT - FLOOR_HEIGHT))
    except pygame.error as e:
        print(f"Error drawing floor: {e}")


def _generate_floor_surface(width: int, height: int) -> pygame.Surface:
    """Generate floor surface for caching."""
    surface = pygame.Surface((width, height))
    surface.fill(FLOOR_COLOR)
    pygame.draw.line(surface, FLOOR_BORDER_COLOR, (0, 0), (width, 0), 3)
    return surface

def render_text_center(surf: pygame.Surface, text: str, y: int, small: bool = False) -> None:
    """Render text centered on screen with shadow effect.
    
    Args:
        surf: Pygame surface to render on
        text: Text to render
        y: Vertical position
        small: Whether to use smaller font
    """
    try:
        font_size = 28 if small else 42
        font = pygame.font.SysFont(None, font_size)
        
        # Create shadow and main text
        shadow = font.render(text, True, (0, 0, 0))
        label = font.render(text, True, (255, 255, 255))
        
        # Center the text
        rect = label.get_rect(center=(WIDTH // 2, y))
        srect = shadow.get_rect(center=(WIDTH // 2 + 2, y + 2))
        
        # Draw shadow first, then main text
        surf.blit(shadow, srect)
        surf.blit(label, rect)
    except pygame.error as e:
        print(f"Error rendering text '{text}': {e}")

def main():
    """Main game loop with comprehensive performance optimizations."""
    try:
        pygame.init()
        pygame.display.set_caption("Ultra-Optimized Flappy Clone (pygame)")
        
        # Initialize display with error handling
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT))
            if hasattr(pygame.display, 'set_allow_screensaver'):
                pygame.display.set_allow_screensaver(False)  # Better performance
        except pygame.error as e:
            print(f"Failed to create display: {e}")
            sys.exit(1)
        
        clock = pygame.time.Clock()
        
        # Initialize performance systems
        efficiency_manager = EfficiencyManager(screen, FPS)
        performance_monitor = efficiency_manager.monitor
        
        # Enable optimizations
        enable_sprite_caching(True)
        
        # Initialize game systems
        config = GameConfig()
        stats = GameStatistics()
        achievement_manager = AchievementManager()
        
        # Game state
        state = "READY"  # READY -> PLAYING -> PAUSED -> GAMEOVER
        score = 0
        game_start_time = 0.0
        current_flaps = 0
        show_performance = config.get("show_performance", False)
        
        # Achievement notification system
        achievement_notifications: List = []
        notification_display_time = 0.0
        
        # Initialize game objects with object pooling
        bird = Bird(BIRD_X, HEIGHT // 2, BIRD_RADIUS)
        pipe_pool = PipePool(PIPE_POOL_SIZE)
        
        # Spawn timer
        SPAWN_EVENT = USEREVENT + 1
        pygame.time.set_timer(SPAWN_EVENT, SPAWN_MS)

        while True:
            dt = clock.tick(FPS) / 1000.0
            
            # Update performance monitoring
            efficiency_manager.update(dt, clock)
            performance_monitor.increment_draw_calls()
            
            # Update notification timer
            if notification_display_time > 0:
                notification_display_time -= dt
            
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit(0)
                    
                if event.type == KEYDOWN:
                    if event.key == K_SPACE:
                        if state == "READY":
                            state = "PLAYING"
                            game_start_time = time.time()
                            bird.flap()
                            current_flaps = 1
                        elif state == "PLAYING":
                            bird.flap()
                            current_flaps += 1
                        elif state == "GAMEOVER":
                            # ignore space on gameover to avoid accidental restart; use R
                            pass
                    elif event.key == K_r and state == "GAMEOVER":
                        # reset game with cache cleanup
                        state = "READY"
                        score = 0
                        current_flaps = 0
                        bird.reset(BIRD_X, HEIGHT // 2)
                        pipe_pool.clear()
                        achievement_notifications.clear()
                        notification_display_time = 0.0
                        clear_sprite_cache()  # Clear caches on reset
                    elif event.key == K_p and state == "PLAYING":
                        # pause/unpause
                        state = "PAUSED"
                    elif event.key == K_p and state == "PAUSED":
                        state = "PLAYING"
                    elif event.key == K_F1:
                        # Toggle performance display
                        show_performance = not show_performance
                        config.set("show_performance", show_performance)
                        
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    if state == "READY":
                        state = "PLAYING"
                        game_start_time = time.time()
                        bird.flap()
                        current_flaps = 1
                    elif state == "PLAYING":
                        bird.flap()
                        current_flaps += 1
                    # ignore clicks on GAMEOVER and PAUSED
                    
                if event.type == SPAWN_EVENT and state == "PLAYING":
                    # Spawn a new pipe pair using object pool
                    new_pipe = pipe_pool.get_pipe(WIDTH + 16, 
                                                 PipePair.random_spawn(WIDTH + 16).gap_y)

            # Update game objects
            if state == "PLAYING":
                bird.update(dt)
                
                # Update pipes using object pool
                pipe_pool.update_all(dt)
                active_pipes = pipe_pool.get_active_pipes()
                
                # Score and achievement tracking
                for pipe in active_pipes:
                    # Score when the pipe fully passes the bird
                    if not pipe.scored and (pipe.x + PIPE_WIDTH) < BIRD_X:
                        old_score = score
                        score += 1
                        pipe.scored = True
                        
                        # Check for perfect pass achievement
                        if is_perfect_pass(bird.y, pipe.gap_y, pipe.gap):
                            stats.perfect_passes += 1
                        
                        # Check for close call
                        if is_close_call(bird.y, bird.radius, pipe.gap_y, pipe.gap):
                            stats.close_calls += 1

            # Collision detection and bounds checking
            if state == "PLAYING":
                # Floor and ceiling collision
                if (bird.y + bird.radius >= (HEIGHT - FLOOR_HEIGHT) or 
                    bird.y - bird.radius <= 0):
                    state = "GAMEOVER"
                    game_time = time.time() - game_start_time
                    stats.update_game_end(score, score, current_flaps, game_time)
                    
                    # Check achievements on game over
                    new_achievements = achievement_manager.check_achievements(
                        stats, score, current_flaps, game_time)
                    if new_achievements:
                        achievement_notifications.extend(new_achievements)
                        notification_display_time = 2.0  # Show for 2 seconds
                else:
                    # Optimized pipe collision detection
                    collision_candidates = pipe_pool.get_collision_candidates(
                        bird.x, bird.y, bird.radius)
                    performance_monitor.increment_collision_checks()
                    
                    if fast_collision_check(bird.x, bird.y, bird.radius, collision_candidates):
                        state = "GAMEOVER"
                        game_time = time.time() - game_start_time
                        stats.update_game_end(score, score, current_flaps, game_time)
                        
                        # Check achievements on game over
                        new_achievements = achievement_manager.check_achievements(
                            stats, score, current_flaps, game_time)
                        if new_achievements:
                            achievement_notifications.extend(new_achievements)
                            notification_display_time = 2.0

            # Optimized Rendering with caching
            try:
                # Use cached background
                background = efficiency_manager.renderer.render_background_cached(
                    SKY_COLOR, not performance_monitor.should_skip_effects())
                screen.blit(background, (0, 0))
                
                # Draw clouds with performance awareness
                draw_clouds_optimized(screen, efficiency_manager.renderer, performance_monitor)
                
                # Batch draw pipes for efficiency
                active_pipes = pipe_pool.get_active_pipes()
                if active_pipes:
                    efficiency_manager.renderer.batch_draw_sprites(active_pipes)
                
                # Draw floor and bird with optimizations
                draw_floor_optimized(screen, efficiency_manager.renderer)
                bird.draw(screen)
                
                # UI rendering based on game state
                if state == "READY":
                    render_text_center(screen, "Click or Space to Flap", HEIGHT // 2 - 80)
                    render_text_center(screen, "Pass pipes to score", HEIGHT // 2 - 35, small=True)
                    render_text_center(screen, "P to pause, F1 for performance", HEIGHT // 2 + 10, small=True)
                elif state == "PLAYING":
                    render_text_center(screen, str(score), 70)
                    
                    # Show FPS if enabled (optimized)
                    if config.get("show_fps", False) and not performance_monitor.should_skip_effects():
                        fps_text = f"FPS: {int(clock.get_fps())}"
                        font = pygame.font.SysFont(None, 24)
                        fps_surface = font.render(fps_text, True, (255, 255, 255))
                        screen.blit(fps_surface, (10, 10))
                elif state == "PAUSED":
                    render_text_center(screen, "PAUSED", HEIGHT // 2 - 40)
                    render_text_center(screen, "Press P to resume", HEIGHT // 2 + 10, small=True)
                elif state == "GAMEOVER":
                    render_text_center(screen, "Game Over", HEIGHT // 2 - 70)
                    render_text_center(screen, f"Score: {score}", HEIGHT // 2 - 30, small=False)
                    if stats.best_score > 0:
                        render_text_center(screen, f"Best: {stats.best_score}", HEIGHT // 2 + 10, small=True)
                    render_text_center(screen, "Press R to restart", HEIGHT // 2 + 50, small=True)
                    
                    # Show some stats (with performance check)
                    if stats.total_games > 1 and not performance_monitor.should_skip_effects():
                        render_text_center(screen, f"Games played: {stats.total_games}", HEIGHT // 2 + 80, small=True)
                
                # Draw achievement notifications
                draw_achievement_notification(screen, achievement_notifications, notification_display_time)
                
                # Performance overlay
                if show_performance:
                    draw_performance_overlay(screen, efficiency_manager)
                
                pygame.display.flip()
                
            except pygame.error as e:
                print(f"Rendering error: {e}")
                
    except Exception as e:
        print(f"Fatal error in main game loop: {e}")
        pygame.quit()
        sys.exit(1)

if __name__ == "__main__":
    main()
