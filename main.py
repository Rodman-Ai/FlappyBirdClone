# main.py — Flappy Bird Enhanced Edition (all 100 features integrated)
"""Async game loop compatible with pygbag for web/mobile deployment.

Desktop:  python main.py
Web:      python -m pygbag main.py  → http://localhost:8000
"""
import asyncio
import pygame
import sys
import time
import math
import random
from datetime import date

# Detect WebAssembly / pygbag environment — some operations must be skipped
_IS_WEB = sys.platform in ("emscripten", "wasm32")
from pygame.locals import (QUIT, KEYDOWN, K_ESCAPE, K_SPACE, K_r, K_p,
                            K_F1, K_F2, K_m, K_h, MOUSEBUTTONDOWN,
                            MOUSEBUTTONUP, USEREVENT)
from typing import List, Optional, Tuple

from settings import (
    WIDTH, HEIGHT, FPS, FLOOR_HEIGHT, BIRD_X, BIRD_RADIUS, SPAWN_MS,
    PIPE_WIDTH, PIPE_GAP, PIPE_SPEED, PIPE_POOL_SIZE,
    MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD, MEDAL_PLATINUM,
    POWERUP_SPAWN_CHANCE, POWERUP_TYPES, POWERUP_COLORS,
    POWERUP_SLOWMO_DURATION, POWERUP_TINY_DURATION, POWERUP_WIDEGAP_PIPES,
    COIN_SPAWN_CHANCE, COIN_VALUE,
    TIME_ATTACK_DURATION, SURVIVAL_LIVES, TURBO_SPEED_MULT,
    TURBO_SCORE_MULT, TINY_BIRD_RADIUS_REDUCTION, SPEEDRUN_TARGET_SCORE,
    DYNAMIC_DIFF_INTERVAL, DYNAMIC_DIFF_SPEED_INC, DYNAMIC_DIFF_GAP_DEC,
    MAX_PIPE_SPEED, MIN_PIPE_GAP,
    WIDE_GAP_CHANCE, NARROW_GAP_CHANCE, WIDE_GAP_MULT, NARROW_GAP_MULT,
    NARROW_GAP_BONUS, FIRST_PIPE_GRACE, COUNTDOWN_DURATION,
    BG_THEMES, FLOOR_THEMES, PIPE_THEMES, DIFFICULTY_PRESETS,
    CHALLENGE_OBJECTIVES, DAILY_STREAK_BONUS,
    PANEL_BG, TITLE_COLOR, MUTED_COLOR, SKY_COLOR,
    FLOOR_COLOR, FLOOR_BORDER_COLOR, CLOUD_COLOR,
)
from sprites import (
    Bird, PipePair, PipePool, GhostBird, Coin, PowerUpItem,
    fast_collision_check, is_perfect_pass, is_close_call,
    enable_sprite_caching, clear_sprite_cache,
)
from game_stats import (
    GameStatistics, AchievementManager, GameConfig,
    WeeklyChallengeManager, load_stats, save_stats,
)
from performance import EfficiencyManager
from audio import AudioManager
from particles import ParticleSystem
from ui import (
    MainMenuScreen, ModeSelectScreen, SettingsScreen, AchievementsScreen,
    StatsScreen, LeaderboardScreen, CosmeticsScreen, TutorialScreen,
    PauseMenuScreen, GameOverScreen,
    draw_lives_hud, draw_timer_hud, draw_powerup_hud, draw_combo_hud,
    draw_streak_hud, draw_speed_hud, draw_mute_button, draw_challenge_hud,
    draw_vignette, get_medal_color,
)


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _generate_floor_tile(width: int, height: int, theme: str) -> pygame.Surface:
    pal = FLOOR_THEMES.get(theme, FLOOR_THEMES["grass"])
    s = pygame.Surface((width * 2, height))
    s.fill(pal["fill"])
    pygame.draw.line(s, pal["border"], (0, 0), (width * 2, 0), 3)
    # Tile pattern
    for tx in range(0, width * 2, 32):
        pygame.draw.line(s, pal["border"], (tx, 0), (tx, height), 1)
    return s


def draw_floor(surf: pygame.Surface, offset: float, theme: str,
               renderer) -> None:
    """Scrolling floor tile (feature #7)."""
    try:
        tile = renderer.get_cached_surface(
            f"floor_{theme}", _generate_floor_tile, WIDTH, FLOOR_HEIGHT, theme)
        ox = -int(offset) % WIDTH
        surf.blit(tile, (ox, HEIGHT - FLOOR_HEIGHT))
        surf.blit(tile, (ox - WIDTH, HEIGHT - FLOOR_HEIGHT))
    except Exception:
        pal = FLOOR_THEMES.get(theme, FLOOR_THEMES["grass"])
        pygame.draw.rect(surf, pal["fill"],
                         pygame.Rect(0, HEIGHT - FLOOR_HEIGHT, WIDTH, FLOOR_HEIGHT))
        pygame.draw.line(surf, pal["border"],
                         (0, HEIGHT - FLOOR_HEIGHT), (WIDTH, HEIGHT - FLOOR_HEIGHT), 3)


def render_text_center(surf: pygame.Surface, text: str, y: int,
                       small: bool = False, large: bool = False) -> None:
    size = 28 if small else 42
    if large:
        size = int(size * 1.5)
    font = pygame.font.SysFont(None, size)
    shadow = font.render(text, True, (0, 0, 0))
    label = font.render(text, True, (255, 255, 255))
    rect = label.get_rect(center=(WIDTH // 2, y))
    surf.blit(shadow, shadow.get_rect(center=(WIDTH // 2 + 2, y + 2)))
    surf.blit(label, rect)


def draw_achievement_notification(surf: pygame.Surface, notifications: list,
                                  display_time: float) -> None:
    if not notifications or display_time <= 0:
        return
    latest = notifications[-1]
    alpha = min(200, int(display_time * 150))
    panel = pygame.Surface((WIDTH - 40, 44), pygame.SRCALPHA)
    panel.fill((0, 0, 0, alpha))
    surf.blit(panel, (20, HEIGHT - 110))
    render_text_center(surf, f"Unlocked: {latest.name}!", HEIGHT - 95, small=True)


def draw_performance_overlay(surf: pygame.Surface, eff_mgr) -> None:
    info = eff_mgr.get_performance_info()
    font = pygame.font.SysFont(None, 20)
    lines = [
        f"FPS: {info['fps']:.1f}",
        f"Frame: {info['frame_time_ms']:.1f} ms",
        f"Mem: {info['memory_mb']:.1f} MB",
        f"Quality: {info['quality_level']:.2f}",
        f"Cache hit: {info['cache_hit_rate']:.0f}%",
    ]
    panel = pygame.Surface((148, len(lines) * 18 + 10), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    surf.blit(panel, (5, 30))
    for i, line in enumerate(lines):
        surf.blit(font.render(line, True, (80, 255, 80)), (10, 35 + i * 18))


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def get_sky_color(bg_theme: str, day_t: float) -> tuple:
    """Interpolate sky color for day/night cycle (feature #16)."""
    theme = BG_THEMES.get(bg_theme, BG_THEMES["day"])
    base = theme["sky"]
    night = BG_THEMES["night"]["sky"]
    if bg_theme == "night":
        return base
    t = max(0.0, min(1.0, day_t))
    return _lerp_color(base, night, t * 0.4)


def draw_parallax_clouds(surf: pygame.Surface, offsets1: List[float],
                         offsets2: List[float], theme: str) -> None:
    """Two-layer parallax clouds (feature #8)."""
    bg = BG_THEMES.get(theme, BG_THEMES["day"])
    cloud_col = bg["clouds"]

    def _cloud(cx: float, cy: int, r: int) -> None:
        pygame.draw.circle(surf, cloud_col, (int(cx), cy), r)
        pygame.draw.circle(surf, cloud_col, (int(cx) + r, cy + 4), int(r * 0.8))
        pygame.draw.circle(surf, cloud_col, (int(cx) - r, cy + 4), int(r * 0.7))

    for ox in offsets1:
        _cloud(ox % (WIDTH + 100) - 50, 90, 22)
    for ox in offsets2:
        _cloud(ox % (WIDTH + 80) - 40, 145, 16)


def draw_motion_trail(surf: pygame.Surface,
                      trail: List[Tuple[float, float, float]]) -> None:
    """Ghost copies of bird fading behind it (feature #13)."""
    for i, (tx, ty, ta) in enumerate(trail):
        alpha = int(60 * (i + 1) / len(trail))
        ghost = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(ghost, (250, 210, 70, alpha), (20, 20), 14)
        surf.blit(ghost, (int(tx) - 20, int(ty) - 20))


# ---------------------------------------------------------------------------
# Mutable game state namespace (avoids nonlocal in every closure)
# ---------------------------------------------------------------------------

class _GS:
    __slots__ = (
        "running", "state", "active_screen", "prev_screen_state",
        "game_mode", "score", "pipes_passed", "current_flaps",
        "game_start_time", "lives", "time_left", "speedrun_start_time",
        "current_pipe_speed", "current_gap", "pipes_since_diff",
        "first_pipe_spawned",
        "combo", "streak", "combo_peak",
        "coins_on_screen", "coins_session",
        "powerups_on_screen",
        "shield_active", "slowmo_active", "tiny_active", "widegap_remaining",
        "active_powerup_type", "active_powerup_max_time", "active_powerup_timer",
        "challenge_progress", "challenge_done", "challenge_objectives",
        "current_run_frames", "ghost_bird", "motion_trail",
        "floor_offset", "cloud1_offsets", "cloud2_offsets", "day_t",
        "close_call_pulse", "game_frozen", "freeze_timer",
        "achievement_notifications", "notification_display_time",
        "game_over_result",
    )


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

async def main() -> None:
    pygame.init()
    pygame.display.set_caption("Flappy Bird Enhanced")

    config = GameConfig()
    stats = load_stats()
    achievement_manager = AchievementManager()
    weekly = WeeklyChallengeManager()
    audio = AudioManager()
    particles = ParticleSystem()

    # ---- Display setup (no SCALED/FULLSCREEN on web) ----
    flags = 0
    if not _IS_WEB:
        if config.get("fullscreen", False):
            flags |= pygame.FULLSCREEN
        if config.get("vsync", False):
            flags |= pygame.SCALED
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    except Exception as e:
        print(f"[display] fallback: {e}")
        screen = pygame.display.set_mode((WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    efficiency_manager = EfficiencyManager(screen, FPS)
    perf = efficiency_manager.monitor
    enable_sprite_caching(True)

    # ---- Audio init (music skipped on web — too slow to synthesize) ----
    # Yield to browser before the blocking PCM synthesis loop
    await asyncio.sleep(0)
    audio.init()
    audio.set_sfx_volume(config.get("sfx_volume", 0.5))
    audio.set_music_volume(config.get("music_volume", 0.25))
    audio.set_muted(config.get("muted", False))
    if not _IS_WEB and config.get("music_enabled", True):
        audio.play_music()

    # Gamepad
    pygame.joystick.init()
    joysticks = []
    for i in range(min(4, pygame.joystick.get_count())):
        try:
            j = pygame.joystick.Joystick(i)
            j.init()
            joysticks.append(j)
        except Exception:
            pass

    # ---- Game objects ----
    bird = Bird(BIRD_X, HEIGHT // 2, BIRD_RADIUS, config.get("active_skin", "classic"))
    pipe_pool = PipePool(PIPE_POOL_SIZE)

    SPAWN_EVENT = USEREVENT + 1
    pygame.time.set_timer(SPAWN_EVENT, SPAWN_MS)

    # ---- Mutable state ----
    gs = _GS()
    gs.running = True
    gs.state = "MAINMENU"
    gs.active_screen = None
    gs.prev_screen_state = "MAINMENU"

    gs.game_mode = config.get("game_mode", "CLASSIC")
    gs.score = 0
    gs.pipes_passed = 0
    gs.current_flaps = 0
    gs.game_start_time = 0.0
    gs.lives = SURVIVAL_LIVES
    gs.time_left = TIME_ATTACK_DURATION
    gs.speedrun_start_time = 0.0

    gs.current_pipe_speed = PIPE_SPEED
    gs.current_gap = PIPE_GAP
    gs.pipes_since_diff = 0
    gs.first_pipe_spawned = False

    gs.combo = 1
    gs.streak = 0
    gs.combo_peak = 1

    gs.coins_on_screen: List[Coin] = []
    gs.coins_session = 0
    gs.powerups_on_screen: List[PowerUpItem] = []

    gs.shield_active = False
    gs.slowmo_active = 0.0
    gs.tiny_active = 0.0
    gs.widegap_remaining = 0
    gs.active_powerup_type = None
    gs.active_powerup_max_time = 1.0
    gs.active_powerup_timer = 0.0

    gs.challenge_progress = {}
    gs.challenge_done = False
    gs.challenge_objectives: List[tuple] = []

    gs.current_run_frames: List[Tuple[float, float]] = []
    gs.ghost_bird: Optional[GhostBird] = None
    gs.motion_trail: List[Tuple[float, float, float]] = []

    gs.floor_offset = 0.0
    gs.cloud1_offsets = [60.0, 200.0, 370.0, 550.0, 720.0]
    gs.cloud2_offsets = [130.0, 320.0, 520.0]
    gs.day_t = 0.0

    gs.close_call_pulse = 0.0
    gs.game_frozen = False
    gs.freeze_timer = 0.0

    gs.achievement_notifications: List = []
    gs.notification_display_time = 0.0
    gs.game_over_result = {}

    # ---- Initial screen ----
    large = config.get("large_text", False)
    if not config.get("first_run_done", False):
        gs.active_screen = TutorialScreen(large_text=large)
        gs.state = "TUTORIAL"
    else:
        gs.active_screen = MainMenuScreen(large_text=large)
        gs.state = "MAINMENU"

    # ---- Helpers ----

    def _large() -> bool:
        return config.get("large_text", False)

    def _reduced_motion() -> bool:
        return config.get("reduced_motion", False)

    def _get_spawn_ms() -> int:
        preset = DIFFICULTY_PRESETS.get(config.get("difficulty", "normal"),
                                        DIFFICULTY_PRESETS["normal"])
        ms = SPAWN_MS + preset.get("spawn_offset_ms", 0)
        if gs.game_mode == "TURBO":
            ms = int(ms * 0.6)
        return max(600, ms)

    def _base_speed() -> float:
        preset = DIFFICULTY_PRESETS.get(config.get("difficulty", "normal"),
                                        DIFFICULTY_PRESETS["normal"])
        speed = PIPE_SPEED * preset.get("speed_mult", 1.0)
        if gs.game_mode == "TURBO":
            speed *= TURBO_SPEED_MULT
        return speed * config.get("speed_mult", 1.0)

    def _base_gap() -> int:
        preset = DIFFICULTY_PRESETS.get(config.get("difficulty", "normal"),
                                        DIFFICULTY_PRESETS["normal"])
        return PIPE_GAP + preset.get("gap_offset", 0)

    def _apply_display() -> None:
        nonlocal screen
        flags = 0
        if config.get("fullscreen", False):
            flags |= pygame.FULLSCREEN
        if config.get("vsync", False):
            flags |= pygame.SCALED
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except Exception as e:
            print(f"[display] {e}")

    def _go_to_main_menu() -> None:
        gs.active_screen = MainMenuScreen(large_text=_large())
        gs.state = "MAINMENU"
        pygame.time.set_timer(SPAWN_EVENT, SPAWN_MS)
        pipe_pool.clear()
        gs.coins_on_screen.clear()
        gs.powerups_on_screen.clear()

    def _do_flap() -> None:
        if gs.game_frozen:
            return
        bird.flap()
        gs.current_flaps += 1
        if not _reduced_motion():
            particles.emit_flap(bird.x, bird.y)
        audio.play("flap")

    def _spawn_pipe() -> None:
        effective_speed = gs.current_pipe_speed
        if gs.slowmo_active > 0:
            effective_speed *= 0.5

        gap_y = PipePair.random_gap_y()
        gap_size = gs.current_gap
        variant = "normal"

        if not gs.first_pipe_spawned:
            gap_size += FIRST_PIPE_GRACE
            gs.first_pipe_spawned = True

        if gs.widegap_remaining > 0:
            gap_size = int(gs.current_gap * WIDE_GAP_MULT)
            gs.widegap_remaining -= 1
            variant = "wide"
        else:
            rng = random.random()
            if rng < NARROW_GAP_CHANCE:
                variant = "narrow"
                gap_size = int(gs.current_gap * NARROW_GAP_MULT)
            elif rng < NARROW_GAP_CHANCE + WIDE_GAP_CHANCE:
                variant = "wide"
                gap_size = int(gs.current_gap * WIDE_GAP_MULT)

        moving = (gs.game_mode == "CHALLENGE" and random.random() < 0.3)

        theme = config.get("pipe_theme", "classic")
        if gs.game_mode == "NIGHT":
            theme = "ice"

        pipe = pipe_pool.get_pipe(WIDTH + 16, gap_y, theme=theme,
                                  moving=moving, variant=variant,
                                  gap_override=gap_size)
        pipe.speed = effective_speed

        # Coins in gap
        if random.random() < COIN_SPAWN_CHANCE:
            cx = WIDTH + 16 + PIPE_WIDTH // 2 + 16
            cy = gap_y + random.randint(-30, 30)
            gs.coins_on_screen.append(Coin(cx, cy))

        # Power-ups
        if random.random() < POWERUP_SPAWN_CHANCE and gs.game_mode != "ZEN":
            px = WIDTH + 16 + PIPE_WIDTH // 2 + 50
            py = gap_y + random.randint(-20, 20)
            ptype = random.choice(POWERUP_TYPES)
            gs.powerups_on_screen.append(PowerUpItem(px, py, ptype))

    def _activate_powerup(ptype: str) -> None:
        audio.play("powerup")
        if not _reduced_motion():
            particles.emit_powerup(0, 0, POWERUP_COLORS.get(ptype, (200, 200, 200)))
        gs.active_powerup_type = ptype
        if ptype == "shield":
            gs.shield_active = True
            gs.active_powerup_max_time = 30.0
            gs.active_powerup_timer = 30.0
        elif ptype == "slowmo":
            gs.slowmo_active = POWERUP_SLOWMO_DURATION
            gs.active_powerup_max_time = POWERUP_SLOWMO_DURATION
            gs.active_powerup_timer = POWERUP_SLOWMO_DURATION
        elif ptype == "tiny":
            gs.tiny_active = POWERUP_TINY_DURATION
            gs.active_powerup_max_time = POWERUP_TINY_DURATION
            gs.active_powerup_timer = POWERUP_TINY_DURATION
            bird.radius = max(6, BIRD_RADIUS - TINY_BIRD_RADIUS_REDUCTION - 4)
        elif ptype == "widegap":
            gs.widegap_remaining = POWERUP_WIDEGAP_PIPES
            gs.active_powerup_max_time = float(POWERUP_WIDEGAP_PIPES)
            gs.active_powerup_timer = float(POWERUP_WIDEGAP_PIPES)

    def _start_gameplay(mode: str) -> None:
        gs.game_mode = mode
        config.set("game_mode", mode)

        gs.score = 0
        gs.pipes_passed = 0
        gs.current_flaps = 0
        gs.combo = 1
        gs.streak = 0
        gs.combo_peak = 1
        gs.coins_session = 0

        gs.shield_active = False
        gs.slowmo_active = 0.0
        gs.tiny_active = 0.0
        gs.widegap_remaining = 0
        gs.active_powerup_type = None
        gs.active_powerup_timer = 0.0
        gs.active_powerup_max_time = 1.0

        gs.coins_on_screen.clear()
        gs.powerups_on_screen.clear()

        gs.current_pipe_speed = _base_speed()
        gs.current_gap = _base_gap()
        gs.pipes_since_diff = 0
        gs.first_pipe_spawned = False

        gs.lives = SURVIVAL_LIVES
        gs.time_left = TIME_ATTACK_DURATION
        gs.speedrun_start_time = time.time()

        gs.challenge_progress = {}
        gs.challenge_done = False
        gs.challenge_objectives = list(CHALLENGE_OBJECTIVES)

        gs.current_run_frames.clear()
        if stats.best_run_frames:
            gs.ghost_bird = GhostBird(
                [(y, a) for y, a in stats.best_run_frames],
                BIRD_X - 22, BIRD_RADIUS)
        else:
            gs.ghost_bird = None

        bird_radius = BIRD_RADIUS
        if mode in ("TINY_BIRD",):
            bird_radius = BIRD_RADIUS - TINY_BIRD_RADIUS_REDUCTION
        bird.reset(BIRD_X, HEIGHT // 2, skin=config.get("active_skin", "classic"))
        bird.radius = bird_radius

        pipe_pool.clear()
        clear_sprite_cache()
        gs.motion_trail.clear()
        gs.close_call_pulse = 0.0
        gs.game_frozen = False
        gs.freeze_timer = 0.0
        stats.reset_runtime()

        pygame.time.set_timer(SPAWN_EVENT, _get_spawn_ms())
        gs.active_screen = None
        gs.game_start_time = time.time()

        # 3-2-1 countdown (feature #34)
        gs.state = "COUNTDOWN"
        import math as _m
        gs.freeze_timer = float(COUNTDOWN_DURATION)  # reuse as countdown

    def _end_game() -> None:
        if gs.game_mode == "ZEN" or gs.game_mode == "PRACTICE":
            return

        if gs.shield_active:
            gs.shield_active = False
            gs.active_powerup_type = None
            audio.play("shield_hit")
            if not _reduced_motion():
                particles.screen_shake.trigger(0.15, 3.0)
            return

        if gs.game_mode == "SURVIVAL" and gs.lives > 1:
            gs.lives -= 1
            if not _reduced_motion():
                particles.emit_life_lost(bird.x, bird.y)
            audio.play("life_lost")
            bird.reset(BIRD_X, HEIGHT // 2, skin=config.get("active_skin", "classic"))
            gs.game_frozen = True
            gs.freeze_timer = 0.20
            return

        audio.play("death")
        if not _reduced_motion():
            particles.emit_death(bird.x, bird.y)
            particles.screen_shake.trigger(0.30, 6.0)

        game_time = time.time() - gs.game_start_time
        is_new_best = stats.update_game_end(
            gs.score, gs.pipes_passed, gs.current_flaps, game_time)

        if is_new_best and gs.game_mode not in ("PRACTICE", "ZEN"):
            stats.best_run_frames = list(gs.current_run_frames)
            if not _reduced_motion():
                particles.emit_best_score(WIDTH)
            audio.play("new_best")

        if gs.game_mode not in ("PRACTICE",):
            stats.add_leaderboard_entry(
                gs.score, config.get("player_name", "Player"), gs.game_mode)

        stats.add_coins(gs.coins_session)
        stats.coin_balance += gs.coins_session

        weekly.update("pipes", gs.pipes_passed)
        weekly.update("perfects", stats.perfect_passes)
        weekly.update("close_calls", stats.close_calls)
        weekly.update("flaps", gs.current_flaps)

        if gs.score >= MEDAL_GOLD and not _reduced_motion():
            audio.play("medal")
        elif gs.score >= MEDAL_BRONZE:
            pass  # regular score

        new_ach = achievement_manager.check_achievements(
            stats, gs.score, gs.current_flaps, game_time,
            gs.combo_peak, stats.coin_balance,
            gs.game_mode, gs.challenge_done)
        if new_ach:
            gs.achievement_notifications.extend(new_ach)
            gs.notification_display_time = 2.5
            audio.play("achievement")

        medal_name = ""
        if gs.score >= MEDAL_PLATINUM:
            medal_name = "PLATINUM"
        elif gs.score >= MEDAL_GOLD:
            medal_name = "GOLD"
        elif gs.score >= MEDAL_SILVER:
            medal_name = "SILVER"
        elif gs.score >= MEDAL_BRONZE:
            medal_name = "BRONZE"

        gs.game_over_result = {
            "score": gs.score,
            "best_score": stats.best_score,
            "is_new_best": is_new_best,
            "medal": medal_name,
            "pipes": gs.pipes_passed,
            "perfects": stats.perfect_passes,
            "close_calls": stats.close_calls,
            "combo_peak": gs.combo_peak,
            "game_time": game_time,
            "game_mode": gs.game_mode,
            "lives_remaining": gs.lives,
            "challenge_done": gs.challenge_done,
            "daily_best": stats.daily_best_score,
            "session_best": stats.session_best_score,
        }

        save_stats(stats)
        weekly.save()

        gs.game_frozen = True
        gs.freeze_timer = 0.15
        gs.state = "GAMEOVER_FREEZE"

    def _handle_screen_action(action: Optional[str]) -> None:
        if not action:
            return
        large = _large()

        if action == "QUIT":
            gs.running = False

        elif action == "BACK":
            # Return to main menu or previous context
            if gs.prev_screen_state in ("PAUSED",):
                gs.active_screen = PauseMenuScreen(large_text=large)
                gs.state = "PAUSED"
            else:
                _go_to_main_menu()

        elif action == "RESUME":
            gs.active_screen = None
            gs.state = "PLAYING"
            gs.game_frozen = False

        elif action == "RESTART":
            _start_gameplay(gs.game_mode)

        elif action == "MAINMENU":
            _go_to_main_menu()

        elif action == "PLAYING":
            _start_gameplay(config.get("game_mode", "CLASSIC"))

        elif action == "MODESELECT":
            gs.prev_screen_state = gs.state
            gs.active_screen = ModeSelectScreen(gs.game_mode, large_text=large)
            gs.state = "MODESELECT"

        elif action.startswith("MODE:"):
            mode = action[5:]
            gs.game_mode = mode
            config.set("game_mode", mode)
            _start_gameplay(mode)

        elif action == "SETTINGS":
            gs.prev_screen_state = gs.state
            gs.active_screen = SettingsScreen(config, audio, large_text=large)
            gs.state = "SETTINGS"

        elif action == "RELOAD_SETTINGS":
            _apply_display()
            large2 = _large()
            gs.active_screen = SettingsScreen(config, audio, large_text=large2)
            gs.state = "SETTINGS"

        elif action == "ACHIEVEMENTS":
            gs.prev_screen_state = gs.state
            gs.active_screen = AchievementsScreen(achievement_manager,
                                                  large_text=large)
            gs.state = "ACHIEVEMENTS"

        elif action == "STATS":
            gs.prev_screen_state = gs.state
            gs.active_screen = StatsScreen(stats, large_text=large)
            gs.state = "STATS"

        elif action == "LEADERBOARD":
            gs.prev_screen_state = gs.state
            gs.active_screen = LeaderboardScreen(stats, large_text=large)
            gs.state = "LEADERBOARD"

        elif action == "COSMETICS":
            gs.prev_screen_state = gs.state
            config.config["coin_balance"] = stats.coin_balance
            gs.active_screen = CosmeticsScreen(config, achievement_manager,
                                               large_text=large)
            gs.state = "COSMETICS"

        elif action == "TUTORIAL":
            gs.prev_screen_state = gs.state
            gs.active_screen = TutorialScreen(large_text=large)
            gs.state = "TUTORIAL"

        elif action == "DONE":
            # Tutorial done
            config.set("first_run_done", True)
            _go_to_main_menu()

    # ---- Main loop ----
    while gs.running:
        fps_cap = config.get("fps_cap", FPS)
        if fps_cap <= 0:
            fps_cap = 0
        dt = clock.tick(fps_cap) / 1000.0
        dt = min(dt, 0.1)

        efficiency_manager.update(dt, clock)

        if gs.notification_display_time > 0:
            gs.notification_display_time -= dt

        # ---- Events ----
        for event in pygame.event.get():
            if event.type == QUIT:
                gs.running = False
                break

            # Global: screenshot (F2)
            if event.type == KEYDOWN and event.key == K_F2:
                fname = f"screenshot_{date.today().isoformat()}_{int(time.time())}.png"
                try:
                    pygame.image.save(screen, fname)
                    print(f"[screenshot] {fname}")
                except Exception as e:
                    print(f"[screenshot] {e}")

            # Global: F1 toggle perf overlay
            if event.type == KEYDOWN and event.key == K_F1:
                config.set("show_performance",
                           not config.get("show_performance", False))

            # Global: M = mute toggle
            if event.type == KEYDOWN and event.key == K_m:
                new_muted = not config.get("muted", False)
                config.set("muted", new_muted)
                audio.set_muted(new_muted)

            # Gamepad flap
            if event.type == pygame.JOYBUTTONDOWN:
                if gs.state in ("COUNTDOWN", "PLAYING"):
                    _do_flap()
                elif gs.active_screen is not None and gs.state == "MAINMENU":
                    _start_gameplay(gs.game_mode)

            # Active screen routing
            if gs.active_screen is not None:
                action = gs.active_screen.handle_event(event)
                if action:
                    _handle_screen_action(action)
                continue

            # Mute button click (gameplay states)
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                mr = pygame.Rect(WIDTH - 34, 4, 28, 28)
                if mr.collidepoint(event.pos):
                    new_muted = not config.get("muted", False)
                    config.set("muted", new_muted)
                    audio.set_muted(new_muted)
                    continue

            # Gameplay events
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    if gs.state in ("PLAYING", "COUNTDOWN"):
                        gs.prev_screen_state = gs.state
                        gs.active_screen = PauseMenuScreen(large_text=_large())
                        gs.state = "PAUSED"
                    elif gs.state in ("GAMEOVER", "GAMEOVER_FREEZE"):
                        _go_to_main_menu()
                    else:
                        gs.running = False
                elif event.key == K_SPACE:
                    if gs.state in ("COUNTDOWN", "PLAYING"):
                        _do_flap()
                    elif gs.state == "GAMEOVER":
                        _start_gameplay(gs.game_mode)
                elif event.key == K_r and gs.state == "GAMEOVER":
                    _start_gameplay(gs.game_mode)
                elif event.key == K_p and gs.state == "PLAYING":
                    gs.prev_screen_state = "PLAYING"
                    gs.active_screen = PauseMenuScreen(large_text=_large())
                    gs.state = "PAUSED"

            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if gs.state in ("COUNTDOWN", "PLAYING"):
                    _do_flap()
                elif gs.state == "GAMEOVER":
                    _start_gameplay(gs.game_mode)

            elif event.type == pygame.FINGERDOWN:
                if gs.state in ("COUNTDOWN", "PLAYING"):
                    _do_flap()
                elif gs.state == "GAMEOVER":
                    _start_gameplay(gs.game_mode)

            elif event.type == SPAWN_EVENT and gs.state == "PLAYING":
                _spawn_pipe()

        # ---- Update ----
        if gs.active_screen is not None:
            gs.active_screen.update(dt)

        elif gs.state == "COUNTDOWN":
            gs.freeze_timer -= dt
            if gs.freeze_timer <= 0:
                gs.state = "PLAYING"
                gs.freeze_timer = 0.0
                audio.play("go")
            elif gs.freeze_timer <= float(COUNTDOWN_DURATION) - 1.0:
                pass  # tick every second handled by draw
            bird.update(dt)

        elif gs.state == "PLAYING":
            if gs.game_frozen:
                gs.freeze_timer -= dt
                if gs.freeze_timer <= 0:
                    gs.game_frozen = False
                    if gs.state != "GAMEOVER_FREEZE":
                        gs.state = "PLAYING"
            else:
                # Scroll visuals
                effective_speed = gs.current_pipe_speed
                if gs.slowmo_active > 0:
                    effective_speed *= 0.5
                gs.floor_offset += effective_speed * dt * 60
                if gs.floor_offset >= WIDTH:
                    gs.floor_offset -= WIDTH

                for i in range(len(gs.cloud1_offsets)):
                    gs.cloud1_offsets[i] -= effective_speed * 0.3 * dt * 60
                for i in range(len(gs.cloud2_offsets)):
                    gs.cloud2_offsets[i] -= effective_speed * 0.18 * dt * 60

                # Day/night cycle (feature #16)
                if gs.game_mode != "NIGHT":
                    gs.day_t = (gs.day_t + dt * 0.004) % 2.0
                else:
                    gs.day_t = 1.0

                # Stars in night mode
                if (BG_THEMES.get(config.get("bg_theme", "day"), {}).get("stars")
                        or gs.game_mode == "NIGHT"):
                    if random.random() < 0.3 and not _reduced_motion():
                        particles.emit_stars(WIDTH, HEIGHT, 1)

                bird.update(dt)
                pipe_pool.update_all(dt)

                # Power-up timers
                if gs.slowmo_active > 0:
                    gs.slowmo_active -= dt
                    gs.active_powerup_timer = gs.slowmo_active
                    if gs.slowmo_active <= 0:
                        gs.slowmo_active = 0.0
                        if gs.active_powerup_type == "slowmo":
                            gs.active_powerup_type = None
                if gs.tiny_active > 0:
                    gs.tiny_active -= dt
                    gs.active_powerup_timer = gs.tiny_active
                    if gs.tiny_active <= 0:
                        gs.tiny_active = 0.0
                        bird.radius = BIRD_RADIUS
                        if gs.active_powerup_type == "tiny":
                            gs.active_powerup_type = None

                # Coins update & collect
                for coin in gs.coins_on_screen[:]:
                    coin.update(dt, effective_speed)
                    if coin.active and coin.collect_check(bird.x, bird.y, bird.radius):
                        coin.active = False
                        gs.coins_session += COIN_VALUE
                        if not _reduced_motion():
                            particles.emit_coin(coin.x, coin.y)
                        audio.play("coin")
                        weekly.update("coins", COIN_VALUE)
                gs.coins_on_screen = [c for c in gs.coins_on_screen
                                      if c.active and not c.off_screen]

                # Power-ups update & collect
                for pu in gs.powerups_on_screen[:]:
                    pu.update(dt, effective_speed)
                    if pu.active and pu.collect_check(bird.x, bird.y, bird.radius):
                        pu.active = False
                        _activate_powerup(pu.ptype)
                gs.powerups_on_screen = [p for p in gs.powerups_on_screen
                                         if p.active and not p.off_screen]

                # Scoring
                for pipe in pipe_pool.get_active_pipes():
                    if not pipe.scored and (pipe.x + pipe.width) < BIRD_X:
                        base_pts = 1
                        if gs.game_mode == "TURBO":
                            base_pts = TURBO_SCORE_MULT
                        if pipe.variant == "narrow":
                            base_pts += NARROW_GAP_BONUS
                        pts = base_pts * gs.combo

                        gs.score += pts
                        gs.pipes_passed += 1
                        pipe.scored = True

                        # Combo / streak
                        if is_perfect_pass(bird.y, pipe.gap_y, pipe.gap):
                            stats.perfect_passes += 1
                            gs.combo = min(gs.combo + 1, 5)
                            if not _reduced_motion():
                                particles.emit_score(pipe.x + pipe.width // 2, pipe.gap_y)
                            if gs.combo > 1:
                                audio.play("combo")
                        else:
                            gs.combo = max(1, gs.combo - 1)
                            if not _reduced_motion():
                                particles.emit_score(pipe.x + pipe.width // 2, pipe.gap_y)

                        gs.streak += 1
                        if gs.combo > gs.combo_peak:
                            gs.combo_peak = gs.combo
                        stats.current_combo = gs.combo
                        stats.current_streak = gs.streak

                        audio.play("score")

                        if is_close_call(bird.y, bird.radius, pipe.gap_y, pipe.gap):
                            stats.close_calls += 1
                            gs.close_call_pulse = 0.6
                            if not _reduced_motion():
                                particles.emit_close_call(bird.x, bird.y)

                        # Survival: perfect pass restores a life
                        if gs.game_mode == "SURVIVAL" and is_perfect_pass(
                                bird.y, pipe.gap_y, pipe.gap) and gs.lives < SURVIVAL_LIVES:
                            gs.lives += 1
                            if not _reduced_motion():
                                particles.emit_life_gain(bird.x, bird.y)
                            audio.play("life_gain")

                        # Dynamic difficulty (feature #29)
                        gs.pipes_since_diff += 1
                        if gs.pipes_since_diff >= DYNAMIC_DIFF_INTERVAL:
                            gs.pipes_since_diff = 0
                            if gs.current_pipe_speed < MAX_PIPE_SPEED:
                                gs.current_pipe_speed = min(
                                    MAX_PIPE_SPEED,
                                    gs.current_pipe_speed + DYNAMIC_DIFF_SPEED_INC)
                            if gs.current_gap > MIN_PIPE_GAP:
                                gs.current_gap = max(
                                    MIN_PIPE_GAP,
                                    gs.current_gap - DYNAMIC_DIFF_GAP_DEC)

                        # Challenge progress
                        if gs.game_mode == "CHALLENGE":
                            for key in ("pipes",):
                                gs.challenge_progress[key] = \
                                    gs.challenge_progress.get(key, 0) + 1

                # Time Attack mode timer
                if gs.game_mode == "TIME_ATTACK":
                    gs.time_left -= dt
                    if gs.time_left <= 0:
                        gs.time_left = 0.0
                        _end_game()

                # Speed Run: done when target reached
                if gs.game_mode == "SPEEDRUN" and gs.score >= SPEEDRUN_TARGET_SCORE:
                    _end_game()

                # Close-call vignette decay
                if gs.close_call_pulse > 0:
                    gs.close_call_pulse -= dt * 2

                # Motion trail (feature #13)
                if not _reduced_motion() and len(gs.motion_trail) > 0:
                    if abs(bird.y - gs.motion_trail[-1][1]) > 2:
                        gs.motion_trail.append((bird.x, bird.y, bird.angle))
                        if len(gs.motion_trail) > 4:
                            gs.motion_trail.pop(0)
                elif not _reduced_motion():
                    gs.motion_trail.append((bird.x, bird.y, bird.angle))

                # Record frames for ghost
                gs.current_run_frames.append((bird.y, bird.angle))
                if len(gs.current_run_frames) > 3600:  # cap at 60s
                    gs.current_run_frames = gs.current_run_frames[-3600:]

                # Ghost bird
                if gs.ghost_bird:
                    gs.ghost_bird.update()

                # Boundary collision
                if (bird.y + bird.radius >= HEIGHT - FLOOR_HEIGHT or
                        bird.y - bird.radius <= 0):
                    _end_game()
                else:
                    candidates = pipe_pool.get_collision_candidates(
                        bird.x, bird.y, bird.radius)
                    if fast_collision_check(bird.x, bird.y, bird.radius, candidates):
                        _end_game()

            particles.update(dt)

        elif gs.state == "GAMEOVER_FREEZE":
            gs.freeze_timer -= dt
            particles.update(dt)
            if gs.freeze_timer <= 0:
                gs.state = "GAMEOVER"
                gs.active_screen = GameOverScreen(
                    gs.game_over_result, large_text=_large())

        # ---- Render ----
        try:
            # Background
            bg_theme = config.get("bg_theme", "day")
            if gs.game_mode == "NIGHT":
                bg_theme = "night"
            sky_col = get_sky_color(bg_theme, gs.day_t)
            screen.fill(sky_col)

            # Parallax clouds (skip in night mode with stars only)
            if not perf.should_skip_effects() and not _reduced_motion():
                draw_parallax_clouds(screen, gs.cloud1_offsets, gs.cloud2_offsets,
                                     bg_theme)

            # Ghost bird
            if (gs.active_screen is None and gs.ghost_bird is not None
                    and gs.state in ("PLAYING", "COUNTDOWN")
                    and not _reduced_motion()):
                gs.ghost_bird.draw(screen)

            # Motion trail
            if gs.motion_trail and not _reduced_motion():
                draw_motion_trail(screen, gs.motion_trail)

            # Pipes + collectibles
            if gs.active_screen is None:
                for pipe in pipe_pool.get_active_pipes():
                    pipe.draw(screen)
                for coin in gs.coins_on_screen:
                    coin.draw(screen)
                for pu in gs.powerups_on_screen:
                    pu.draw(screen)

            # Bird (with screen-shake offset)
            shake_ox, shake_oy = (particles.screen_shake.offset
                                  if not _reduced_motion() else (0, 0))

            if gs.active_screen is None:
                bird_alpha = 128 if gs.game_frozen else 255
                tmp = screen.copy() if shake_ox or shake_oy else None
                bird.draw(screen, alpha=bird_alpha)

            # Floor
            floor_theme = config.get("floor_theme", "grass")
            draw_floor(screen, gs.floor_offset, floor_theme, efficiency_manager.renderer)

            # Particles
            if not _reduced_motion():
                particles.draw(screen)

            # Close-call vignette (feature #14)
            if gs.close_call_pulse > 0 and not _reduced_motion():
                draw_vignette(screen, (255, 50, 50),
                              int(gs.close_call_pulse * 120))

            # Slow-mo tint
            if gs.slowmo_active > 0 and not _reduced_motion():
                draw_vignette(screen, (80, 80, 255), 30)

            # ---- State-specific overlay ----
            if gs.active_screen is not None:
                gs.active_screen.draw(screen)

            elif gs.state == "COUNTDOWN":
                # Score display at top + countdown number
                tick = int(gs.freeze_timer) + 1
                render_text_center(screen, str(tick), HEIGHT // 2 - 30,
                                   large=_large())
                render_text_center(screen, "Get ready!", HEIGHT // 2 + 40,
                                   small=True, large=_large())
                # Countdown audio tick
                if 0 < gs.freeze_timer <= float(COUNTDOWN_DURATION):
                    pass  # sounds handled separately below

            elif gs.state == "PLAYING":
                render_text_center(screen, str(gs.score), 55, large=_large())

                if config.get("show_fps", False):
                    font = pygame.font.SysFont(None, 22)
                    fps_surf = font.render(f"FPS: {int(clock.get_fps())}",
                                          True, (255, 255, 255))
                    screen.blit(fps_surf, (10, 10))

                # Mode HUD
                if gs.game_mode == "SURVIVAL":
                    draw_lives_hud(screen, gs.lives, SURVIVAL_LIVES)
                if gs.game_mode == "TIME_ATTACK":
                    draw_timer_hud(screen, gs.time_left, TIME_ATTACK_DURATION,
                                   large=_large())
                if gs.game_mode == "SPEEDRUN":
                    elapsed = time.time() - gs.speedrun_start_time
                    font = pygame.font.SysFont(None, 26)
                    t = font.render(
                        f"{elapsed:.1f}s  {gs.score}/{SPEEDRUN_TARGET_SCORE}",
                        True, (255, 220, 50))
                    screen.blit(t, t.get_rect(topleft=(20, 8)))
                if gs.game_mode == "CHALLENGE" and gs.challenge_objectives:
                    obj_i = min(gs.pipes_passed, len(gs.challenge_objectives) - 1)
                    label, key, target = gs.challenge_objectives[obj_i]
                    cur_val = gs.challenge_progress.get(key, 0)
                    draw_challenge_hud(screen, label, cur_val, target)

                draw_powerup_hud(screen, gs.active_powerup_type,
                                 gs.active_powerup_timer, gs.active_powerup_max_time)
                draw_combo_hud(screen, gs.combo)
                draw_streak_hud(screen, gs.streak)
                if gs.current_pipe_speed > PIPE_SPEED:
                    draw_speed_hud(screen, gs.current_pipe_speed, MAX_PIPE_SPEED)

                draw_mute_button(screen, config.get("muted", False))

            elif gs.state in ("GAMEOVER", "GAMEOVER_FREEZE"):
                if gs.state == "GAMEOVER_FREEZE":
                    render_text_center(screen, str(gs.score), 70, large=_large())

            # Achievement notification
            draw_achievement_notification(
                screen, gs.achievement_notifications, gs.notification_display_time)

            # Performance overlay
            if config.get("show_performance", False):
                draw_performance_overlay(screen, efficiency_manager)

            # Apply screen shake by shifting final image
            if (not _reduced_motion() and particles.screen_shake.active
                    and gs.active_screen is None):
                ox, oy = particles.screen_shake.offset
                if ox or oy:
                    shifted = screen.copy()
                    screen.fill((0, 0, 0))
                    screen.blit(shifted, (ox, oy))

            pygame.display.flip()

        except Exception as e:
            # Broad catch prevents silent black-screen crashes on web
            print(f"[render] {type(e).__name__}: {e}")
            try:
                # Show a minimal error message so the screen isn't pure black
                screen.fill((10, 10, 30))
                font = pygame.font.SysFont(None, 24)
                msg = font.render(f"Error: {e}", True, (255, 80, 80))
                screen.blit(msg, (10, HEIGHT // 2))
                pygame.display.flip()
            except Exception:
                pass

        await asyncio.sleep(0)

    save_stats(stats)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
