# ui.py — all UI screen classes (features #59-68, #69-75, #76-87)
import pygame
import math
from typing import Optional, List, Callable, Any, Dict

from settings import (
    WIDTH, HEIGHT,
    BUTTON_H, BUTTON_COLOR, BUTTON_HOVER, BUTTON_PRESSED, BUTTON_TEXT,
    PANEL_BG, PANEL_BORDER, TITLE_COLOR, SUBTITLE_COLOR, MUTED_COLOR,
    SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    GAME_MODES, GAME_MODE_LABELS, GAME_MODE_DESCS,
    MEDAL_BRONZE, MEDAL_SILVER, MEDAL_GOLD, MEDAL_PLATINUM,
    BIRD_SKINS, PIPE_THEMES, BG_THEMES, FLOOR_THEMES,
    DEFAULT_SFX_VOLUME, DEFAULT_MUSIC_VOLUME,
)


# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------

def _font(size: int, large_text: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont(None, int(size * (1.5 if large_text else 1.0)))


def _draw_panel(surf: pygame.Surface, rect: pygame.Rect,
                alpha: int = 220) -> None:
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((*PANEL_BG, alpha))
    surf.blit(panel, rect.topleft)
    pygame.draw.rect(surf, PANEL_BORDER, rect, 2, border_radius=6)


def _text(surf: pygame.Surface, text: str, x: int, y: int,
          color: tuple = (255, 255, 255), size: int = 28,
          center: bool = True, large: bool = False) -> None:
    f = _font(size, large)
    rendered = f.render(text, True, color)
    rect = rendered.get_rect(center=(x, y)) if center else rendered.get_rect(topleft=(x, y))
    surf.blit(rendered, rect)


class Button:
    """Clickable button with hover and pressed states."""

    def __init__(self, rect: pygame.Rect, label: str,
                 color: tuple = BUTTON_COLOR,
                 text_color: tuple = BUTTON_TEXT,
                 large_text: bool = False,
                 font_size: int = 26) -> None:
        self.rect = rect
        self.label = label
        self.color = color
        self.text_color = text_color
        self.large_text = large_text
        self.font_size = font_size
        self._hover = False
        self._pressed = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True on click release."""
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self._pressed
            self._pressed = False
            if was and self.rect.collidepoint(event.pos):
                return True
        elif event.type == pygame.FINGERDOWN:
            # Normalize finger position
            fx = int(event.x * WIDTH)
            fy = int(event.y * HEIGHT)
            self._pressed = self.rect.collidepoint(fx, fy)
        elif event.type == pygame.FINGERUP:
            fx = int(event.x * WIDTH)
            fy = int(event.y * HEIGHT)
            was = self._pressed
            self._pressed = False
            if was and self.rect.collidepoint(fx, fy):
                return True
        return False

    def draw(self, surf: pygame.Surface, large_text: bool = False) -> None:
        color = (BUTTON_PRESSED if self._pressed
                 else BUTTON_HOVER if self._hover
                 else self.color)
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, tuple(min(255, c + 40) for c in color[:3]),
                         self.rect, 2, border_radius=8)
        f = _font(self.font_size, large_text or self.large_text)
        lbl = f.render(self.label, True, self.text_color)
        surf.blit(lbl, lbl.get_rect(center=self.rect.center))


class Slider:
    """Horizontal slider returning a 0–1 float (feature #6)."""

    def __init__(self, rect: pygame.Rect, value: float = 0.5,
                 label: str = "") -> None:
        self.rect = rect
        self.value = max(0.0, min(1.0, value))
        self.label = label
        self._dragging = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if value changed."""
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._set_from_x(event.pos[0])
                changed = True
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._set_from_x(event.pos[0])
            changed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        return changed

    def _set_from_x(self, x: int) -> None:
        self.value = max(0.0, min(1.0,
                         (x - self.rect.left) / max(1, self.rect.width)))

    def draw(self, surf: pygame.Surface) -> None:
        # Track
        pygame.draw.rect(surf, (60, 70, 100), self.rect, border_radius=4)
        # Fill
        fill_w = int(self.rect.width * self.value)
        fill_rect = pygame.Rect(self.rect.left, self.rect.top,
                                fill_w, self.rect.height)
        if fill_w > 0:
            pygame.draw.rect(surf, BUTTON_COLOR, fill_rect, border_radius=4)
        # Thumb
        tx = self.rect.left + fill_w
        ty = self.rect.centery
        pygame.draw.circle(surf, (255, 255, 255), (tx, ty), 8)
        pygame.draw.circle(surf, BUTTON_COLOR, (tx, ty), 6)
        # Label
        if self.label:
            f = _font(22)
            lbl = f.render(f"{self.label}: {int(self.value * 100)}%", True,
                           (200, 210, 240))
            surf.blit(lbl, lbl.get_rect(
                midleft=(self.rect.right + 8, self.rect.centery)))


class TextInput:
    """Single-line text input (player name, feature #84)."""

    def __init__(self, rect: pygame.Rect, initial: str = "",
                 max_len: int = 16, placeholder: str = "Enter name…") -> None:
        self.rect = rect
        self.text = initial
        self.max_len = max_len
        self.placeholder = placeholder
        self.active = False
        self._blink = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.active = False
            elif len(self.text) < self.max_len and event.unicode.isprintable():
                self.text += event.unicode
                return True
        return False

    def update(self, dt: float) -> None:
        self._blink = (self._blink + dt) % 1.0

    def draw(self, surf: pygame.Surface) -> None:
        border_col = BUTTON_HOVER if self.active else (60, 70, 100)
        pygame.draw.rect(surf, (30, 35, 55), self.rect, border_radius=6)
        pygame.draw.rect(surf, border_col, self.rect, 2, border_radius=6)
        display = self.text if self.text else self.placeholder
        color = (255, 255, 255) if self.text else MUTED_COLOR
        f = _font(24)
        rendered = f.render(display, True, color)
        surf.blit(rendered, rendered.get_rect(
            midleft=(self.rect.left + 8, self.rect.centery)))
        if self.active and self._blink < 0.5:
            cx = self.rect.left + 8 + rendered.get_width() + 2
            pygame.draw.line(surf, (255, 255, 255),
                             (cx, self.rect.top + 6),
                             (cx, self.rect.bottom - 6), 2)


# ---------------------------------------------------------------------------
# Base screen
# ---------------------------------------------------------------------------

class Screen:
    """Base class for all full-screen UI panels."""

    def __init__(self, large_text: bool = False) -> None:
        self.large_text = large_text
        self._result: Optional[str] = None

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        raise NotImplementedError

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf: pygame.Surface) -> None:
        raise NotImplementedError

    def _btn(self, cx: int, cy: int, w: int, label: str,
             color: tuple = BUTTON_COLOR, font_size: int = 26) -> Button:
        return Button(pygame.Rect(cx - w // 2, cy - BUTTON_H // 2, w, BUTTON_H),
                      label, color=color, font_size=font_size)

    def _header(self, surf: pygame.Surface, title: str) -> None:
        surf.fill(PANEL_BG)
        _text(surf, title, WIDTH // 2, 38, TITLE_COLOR, 40, large=self.large_text)
        pygame.draw.line(surf, PANEL_BORDER, (20, 62), (WIDTH - 20, 62), 1)


# ---------------------------------------------------------------------------
# Main Menu Screen (feature #59)
# ---------------------------------------------------------------------------

class MainMenuScreen(Screen):
    def __init__(self, large_text: bool = False) -> None:
        super().__init__(large_text)
        cx = WIDTH // 2
        self.buttons = {
            "PLAYING":    self._btn(cx, 220, 220, "Play Classic"),
            "MODESELECT": self._btn(cx, 276, 220, "Game Modes"),
            "COSMETICS":  self._btn(cx, 332, 220, "Cosmetics"),
            "ACHIEVEMENTS":self._btn(cx, 388, 220, "Achievements"),
            "STATS":      self._btn(cx, 444, 220, "Statistics"),
            "SETTINGS":   self._btn(cx, 500, 220, "Settings"),
            "QUIT":       self._btn(cx, 556, 220, "Quit",
                                    color=(120, 40, 40)),
        }
        self._time = 0.0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        for action, btn in self.buttons.items():
            if btn.handle_event(event):
                return action
        return None

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(PANEL_BG)
        # Animated title
        bob = int(math.sin(self._time * 2.5) * 4)
        _text(surf, "FLAPPY BIRD", WIDTH // 2, 80 + bob, TITLE_COLOR, 52,
              large=self.large_text)
        _text(surf, "Enhanced Edition", WIDTH // 2, 128, SUBTITLE_COLOR, 26,
              large=self.large_text)
        pygame.draw.line(surf, PANEL_BORDER, (20, 155), (WIDTH - 20, 155), 1)
        for btn in self.buttons.values():
            btn.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Mode Select Screen (feature #38-45, #59)
# ---------------------------------------------------------------------------

class ModeSelectScreen(Screen):
    def __init__(self, current_mode: str = "CLASSIC",
                 large_text: bool = False) -> None:
        super().__init__(large_text)
        self.current_mode = current_mode
        self._back = self._btn(WIDTH // 2, HEIGHT - 34, 120, "Back",
                               color=(80, 80, 120))

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self._back.handle_event(event):
            return "BACK"
        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if event.type == pygame.MOUSEBUTTONUP and event.button != 1:
                return None
            pos = (event.pos if event.type == pygame.MOUSEBUTTONUP
                   else (int(event.x * WIDTH), int(event.y * HEIGHT)))
            for i, mode in enumerate(GAME_MODES):
                rect = self._mode_rect(i)
                if rect.collidepoint(pos):
                    return f"MODE:{mode}"
        return None

    def _mode_rect(self, i: int) -> pygame.Rect:
        col = i % 2
        row = i // 2
        w, h = 180, 56
        x = 12 + col * (w + 8)
        y = 80 + row * (h + 8)
        return pygame.Rect(x, y, w, h)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Game Modes")
        for i, mode in enumerate(GAME_MODES):
            rect = self._mode_rect(i)
            is_cur = mode == self.current_mode
            color = (50, 130, 200) if is_cur else (40, 50, 80)
            _draw_panel(surf, rect, 200)
            pygame.draw.rect(surf, color, rect, 2 if not is_cur else 3,
                             border_radius=6)
            _text(surf, GAME_MODE_LABELS[mode], rect.centerx, rect.top + 18,
                  TITLE_COLOR if is_cur else (220, 230, 255), 22,
                  large=self.large_text)
            desc = GAME_MODE_DESCS[mode]
            if len(desc) > 28:
                desc = desc[:25] + "…"
            _text(surf, desc, rect.centerx, rect.top + 38,
                  MUTED_COLOR, 16, large=self.large_text)
        self._back.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Settings Screen (feature #60, #69-87)
# ---------------------------------------------------------------------------

class SettingsScreen(Screen):
    def __init__(self, config: Any, audio: Any,
                 large_text: bool = False) -> None:
        super().__init__(large_text)
        self.config = config
        self.audio = audio
        cx = WIDTH // 2

        self.sfx_slider = Slider(
            pygame.Rect(20, 110, 220, 12),
            value=config.get("sfx_volume", DEFAULT_SFX_VOLUME), label="SFX")
        self.music_slider = Slider(
            pygame.Rect(20, 148, 220, 12),
            value=config.get("music_volume", DEFAULT_MUSIC_VOLUME), label="Music")

        self.name_input = TextInput(
            pygame.Rect(20, 190, 240, 36),
            initial=config.get("player_name", ""),
            placeholder="Player name…")

        # Toggles: (label, config_key, y)
        self._toggles = [
            ("Fullscreen",     "fullscreen",     256),
            ("VSync",          "vsync",          298),
            ("High Contrast",  "high_contrast",  340),
            ("Reduced Motion", "reduced_motion", 382),
            ("Colorblind",     "colorblind",     424),
            ("Large Text",     "large_text",     466),
            ("Always FPS",     "show_fps",       508),
        ]

        # Difficulty selector
        self._diff_labels = ["easy", "normal", "hard"]
        self._diff_y = 240  # only used when player name is above

        self._reset_btn = self._btn(cx, HEIGHT - 68, 200, "Reset Defaults",
                                    color=(100, 50, 50))
        self._back = self._btn(cx, HEIGHT - 28, 120, "Back",
                               color=(80, 80, 120))

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        changed = self.sfx_slider.handle_event(event)
        if changed:
            self.config.set("sfx_volume", self.sfx_slider.value)
            self.audio.set_sfx_volume(self.sfx_slider.value)

        if self.music_slider.handle_event(event):
            self.config.set("music_volume", self.music_slider.value)
            self.audio.set_music_volume(self.music_slider.value)

        if self.name_input.handle_event(event):
            self.config.set("player_name", self.name_input.text)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = event.pos
            # Toggle buttons
            for label, key, y in self._toggles:
                rect = pygame.Rect(WIDTH - 64, y - 14, 44, 28)
                if rect.collidepoint(pos):
                    new_val = not self.config.get(key, False)
                    self.config.set(key, new_val)
                    self.audio.play("ui_click")
                    if key == "large_text":
                        return "RELOAD_SETTINGS"
            # Difficulty
            diff_y = 232
            for i, d in enumerate(self._diff_labels):
                r = pygame.Rect(20 + i * 76, diff_y - 14, 68, 28)
                if r.collidepoint(pos):
                    self.config.set("difficulty", d)
                    self.audio.play("ui_click")

        if self._reset_btn.handle_event(event):
            self.config.reset_to_defaults()
            self.audio.play("ui_click")
            return "RELOAD_SETTINGS"

        if self._back.handle_event(event):
            self.config.set("player_name", self.name_input.text)
            return "BACK"

        return None

    def update(self, dt: float) -> None:
        self.name_input.update(dt)

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Settings")

        _text(surf, "Player Name", 22, 183, MUTED_COLOR, 20,
              center=False, large=self.large_text)
        self.name_input.draw(surf)

        _text(surf, "Difficulty", 22, 221, MUTED_COLOR, 20,
              center=False, large=self.large_text)
        cur_diff = self.config.get("difficulty", "normal")
        for i, d in enumerate(self._diff_labels):
            r = pygame.Rect(20 + i * 76, 232 - 14, 68, 28)
            col = (50, 130, 200) if d == cur_diff else (40, 50, 80)
            pygame.draw.rect(surf, col, r, border_radius=6)
            pygame.draw.rect(surf, PANEL_BORDER, r, 1, border_radius=6)
            _text(surf, d.capitalize(), r.centerx, r.centery,
                  (255, 255, 255), 20, large=self.large_text)

        # Volume sliders
        _text(surf, "Audio", 22, 95, MUTED_COLOR, 20,
              center=False, large=self.large_text)
        self.sfx_slider.draw(surf)
        self.music_slider.draw(surf)

        # Toggle rows
        for label, key, y in self._toggles:
            _text(surf, label, 22, y, (200, 210, 240), 22,
                  center=False, large=self.large_text)
            on = self.config.get(key, False)
            col = SUCCESS_COLOR if on else (60, 70, 100)
            r = pygame.Rect(WIDTH - 64, y - 14, 44, 28)
            pygame.draw.rect(surf, col, r, border_radius=14)
            cx_t = r.left + (30 if on else 14)
            pygame.draw.circle(surf, (255, 255, 255), (cx_t, r.centery), 12)

        self._reset_btn.draw(surf, self.large_text)
        self._back.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Achievements Screen (feature #61)
# ---------------------------------------------------------------------------

class AchievementsScreen(Screen):
    def __init__(self, ach_manager: Any, large_text: bool = False) -> None:
        super().__init__(large_text)
        self.ach_manager = ach_manager
        self._back = self._btn(WIDTH // 2, HEIGHT - 28, 120, "Back",
                               color=(80, 80, 120))
        self._scroll = 0
        self._max_scroll = 0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self._back.handle_event(event):
            return "BACK"
        if event.type == pygame.MOUSEWHEEL:
            self._scroll = max(0, min(self._max_scroll,
                                      self._scroll - event.y * 30))
        return None

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Achievements")
        achs = list(self.ach_manager.achievements.values())
        row_h = 60
        y0 = 74 - self._scroll
        visible = [a for a in achs if not a.hidden or a.unlocked]
        self._max_scroll = max(0, len(visible) * row_h - (HEIGHT - 100))

        for ach in visible:
            y = y0
            y0 += row_h
            if y < 64 or y > HEIGHT - 44:
                continue
            rect = pygame.Rect(10, y, WIDTH - 20, row_h - 4)
            alpha = 220 if ach.unlocked else 140
            _draw_panel(surf, rect, alpha)

            icon_col = SUCCESS_COLOR if ach.unlocked else MUTED_COLOR
            pygame.draw.circle(surf, icon_col, (28, y + row_h // 2), 10)

            _text(surf, ach.name, 50, y + 14, (255, 255, 255) if ach.unlocked
                  else MUTED_COLOR, 22, center=False, large=self.large_text)
            _text(surf, ach.description, 50, y + 34, MUTED_COLOR, 17,
                  center=False, large=self.large_text)

            if not ach.unlocked and ach.target > 1:
                bar_rect = pygame.Rect(WIDTH - 90, y + row_h // 2 - 5,
                                       72, 10)
                pygame.draw.rect(surf, (50, 60, 80), bar_rect, border_radius=5)
                fill_w = int(72 * ach.progress / max(1, ach.target))
                if fill_w:
                    pygame.draw.rect(surf,
                                     BUTTON_COLOR,
                                     pygame.Rect(bar_rect.x, bar_rect.y,
                                                 fill_w, 10),
                                     border_radius=5)
                _text(surf, f"{ach.progress}/{ach.target}",
                      WIDTH - 54, y + row_h // 2 + 10, MUTED_COLOR, 16)
            elif ach.unlocked:
                _text(surf, "✓", WIDTH - 26, y + row_h // 2,
                      SUCCESS_COLOR, 24)

        self._back.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Statistics Screen (feature #62)
# ---------------------------------------------------------------------------

class StatsScreen(Screen):
    def __init__(self, stats: Any, large_text: bool = False) -> None:
        super().__init__(large_text)
        self.stats = stats
        self._back = self._btn(WIDTH // 2, HEIGHT - 28, 120, "Back",
                               color=(80, 80, 120))

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self._back.handle_event(event):
            return "BACK"
        return None

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Statistics")
        s = self.stats
        rows = [
            ("Total Games",     str(s.total_games)),
            ("Best Score",      str(s.best_score)),
            ("Daily Best",      str(s.daily_best_score)),
            ("Session Best",    str(s.session_best_score)),
            ("Total Pipes",     str(s.total_pipes_passed)),
            ("Perfect Passes",  str(s.perfect_passes)),
            ("Close Calls",     str(s.close_calls)),
            ("Total Flaps",     str(s.total_flaps)),
            ("Coins Collected", str(s.coin_balance)),
            ("Login Streak",    f"{s.daily_streak} day(s)"),
            ("Avg Score",       f"{s.average_score:.1f}"),
            ("Play Time",       f"{s.total_play_time / 60:.1f} min"),
        ]
        row_h = 28
        for i, (label, val) in enumerate(rows):
            y = 74 + i * row_h
            if y > HEIGHT - 50:
                break
            _text(surf, label, 20, y, MUTED_COLOR, 21,
                  center=False, large=self.large_text)
            _text(surf, val, WIDTH - 20, y, (220, 230, 255), 21,
                  center=False, large=self.large_text)

        # Score history graph
        if len(s.score_history) > 1:
            self._draw_graph(surf, s.score_history, 74 + len(rows) * row_h + 8)

        self._back.draw(surf, self.large_text)

    def _draw_graph(self, surf: pygame.Surface,
                    history: List[int], y_top: int) -> None:
        if y_top > HEIGHT - 80:
            return
        gw, gh = WIDTH - 40, min(70, HEIGHT - y_top - 40)
        rect = pygame.Rect(20, y_top, gw, gh)
        _draw_panel(surf, rect, 180)
        _text(surf, "Score History", rect.centerx, y_top - 8,
              MUTED_COLOR, 17)
        if not history:
            return
        mx = max(history) or 1
        pts = []
        for i, sc in enumerate(history):
            x = rect.left + int(i / max(1, len(history) - 1) * (gw - 4)) + 2
            y = rect.bottom - 4 - int(sc / mx * (gh - 8))
            pts.append((x, y))
        if len(pts) > 1:
            pygame.draw.lines(surf, BUTTON_COLOR, False, pts, 2)
        for p in pts:
            pygame.draw.circle(surf, (255, 255, 255), p, 3)


# ---------------------------------------------------------------------------
# Leaderboard Screen (feature #63)
# ---------------------------------------------------------------------------

class LeaderboardScreen(Screen):
    def __init__(self, stats: Any, large_text: bool = False) -> None:
        super().__init__(large_text)
        self.stats = stats
        self._back = self._btn(WIDTH // 2, HEIGHT - 28, 120, "Back",
                               color=(80, 80, 120))

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self._back.handle_event(event):
            return "BACK"
        return None

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Top Scores")
        entries = self.stats.leaderboard
        if not entries:
            _text(surf, "No scores yet — play some games!",
                  WIDTH // 2, HEIGHT // 2, MUTED_COLOR, 24,
                  large=self.large_text)
        else:
            medal_colors = [(255, 215, 0), (192, 192, 192),
                            (205, 127, 50)] + [(150, 160, 180)] * 10
            for i, e in enumerate(entries[:10]):
                y = 80 + i * 46
                rect = pygame.Rect(10, y, WIDTH - 20, 42)
                _draw_panel(surf, rect, 160)
                col = medal_colors[i]
                _text(surf, f"#{i + 1}", 26, y + 21, col, 22,
                      large=self.large_text)
                _text(surf, e.get("name", "Player"), 80, y + 21,
                      (220, 230, 255), 22, center=False, large=self.large_text)
                _text(surf, str(e["score"]), WIDTH - 70, y + 14,
                      TITLE_COLOR, 26, large=self.large_text)
                _text(surf, e.get("mode", ""), WIDTH - 70, y + 32,
                      MUTED_COLOR, 16, large=self.large_text)
                _text(surf, e.get("date", ""), 200, y + 32,
                      MUTED_COLOR, 16, large=self.large_text)
        self._back.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Cosmetics Screen (features #21-27, #64)
# ---------------------------------------------------------------------------

class CosmeticsScreen(Screen):
    def __init__(self, config: Any, ach_manager: Any,
                 large_text: bool = False) -> None:
        super().__init__(large_text)
        self.config = config
        self.ach_manager = ach_manager
        self._back = self._btn(WIDTH // 2, HEIGHT - 28, 120, "Back",
                               color=(80, 80, 120))
        self._section = 0  # 0=skins 1=pipe 2=bg 3=floor
        self._tabs = ["Bird", "Pipes", "Sky", "Floor"]
        self._tab_btns = [
            Button(pygame.Rect(8 + i * 96, 66, 88, 30),
                   self._tabs[i], font_size=20)
            for i in range(4)
        ]

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        for i, tb in enumerate(self._tab_btns):
            if tb.handle_event(event):
                self._section = i
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._handle_click(event.pos)

        if self._back.handle_event(event):
            return "BACK"
        return None

    def _handle_click(self, pos: tuple) -> None:
        items, key = self._current_items()
        for i, item_id in enumerate(items):
            rect = self._item_rect(i)
            if rect.collidepoint(pos):
                if self._is_unlocked(item_id):
                    self.config.set(key, item_id)
                    from sprites import clear_sprite_cache
                    clear_sprite_cache()

    def _current_items(self):
        if self._section == 0:
            return list(BIRD_SKINS.keys()), "active_skin"
        elif self._section == 1:
            return list(PIPE_THEMES.keys()), "pipe_theme"
        elif self._section == 2:
            return list(BG_THEMES.keys()), "bg_theme"
        else:
            return list(FLOOR_THEMES.keys()), "floor_theme"

    def _is_unlocked(self, item_id: str) -> bool:
        if self._section == 0:
            return self.ach_manager.is_skin_unlocked(item_id)
        return True  # themes always unlocked

    def _item_rect(self, i: int) -> pygame.Rect:
        cols = 3
        col = i % cols
        row = i // cols
        w, h = (WIDTH - 24) // cols, 60
        return pygame.Rect(8 + col * (w + 4), 108 + row * (h + 6), w, h)

    def draw(self, surf: pygame.Surface) -> None:
        self._header(surf, "Cosmetics")
        # Coins
        _text(surf, f"Coins: {self.config.get('coin_balance', 0) or 0}",
              WIDTH - 60, 38, (255, 215, 0), 22, large=self.large_text)

        # Tabs
        for i, tb in enumerate(self._tab_btns):
            tb.color = (50, 130, 200) if i == self._section else (40, 50, 80)
            tb.draw(surf, self.large_text)

        items, key = self._current_items()
        cur = self.config.get(key, items[0])
        for i, item_id in enumerate(items):
            rect = self._item_rect(i)
            is_sel = item_id == cur
            unlocked = self._is_unlocked(item_id)
            _draw_panel(surf, rect, 180)
            border_col = (50, 130, 200) if is_sel else (50, 60, 90)
            pygame.draw.rect(surf, border_col, rect, 2 + is_sel, border_radius=6)

            name_col = TITLE_COLOR if is_sel else (220, 230, 255)
            if not unlocked:
                name_col = MUTED_COLOR
            _text(surf, item_id.capitalize(), rect.centerx, rect.centery - 8,
                  name_col, 20, large=self.large_text)

            if not unlocked:
                _text(surf, "🔒", rect.centerx, rect.centery + 12, MUTED_COLOR, 18)
            elif is_sel:
                _text(surf, "✓", rect.centerx, rect.centery + 12, SUCCESS_COLOR, 20)

        self._back.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Tutorial Screen (feature #65)
# ---------------------------------------------------------------------------

class TutorialScreen(Screen):
    STEPS = [
        ("Tap to Flap", "Tap the screen, click, or press Space\nto make the bird flap upward."),
        ("Avoid Pipes", "Fly through the gap between pipes.\nTouch a pipe = game over!"),
        ("Score Points", "Every pipe you pass scores a point.\nHow high can you go?"),
    ]

    def __init__(self, large_text: bool = False) -> None:
        super().__init__(large_text)
        self._step = 0
        self._next_btn = self._btn(WIDTH // 2, HEIGHT - 100, 180, "Next →")
        self._skip_btn = self._btn(WIDTH // 2, HEIGHT - 50, 120, "Skip",
                                   color=(80, 80, 120), font_size=22)
        self._time = 0.0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self._skip_btn.handle_event(event):
            return "DONE"
        if self._next_btn.handle_event(event):
            self._step += 1
            if self._step >= len(self.STEPS):
                return "DONE"
            self._next_btn.label = "Got it!" if self._step == len(self.STEPS) - 1 else "Next →"
        # Tap anywhere advances
        if event.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
            return None  # handled by buttons above
        return None

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(PANEL_BG)
        _text(surf, f"Step {self._step + 1} / {len(self.STEPS)}",
              WIDTH // 2, 40, MUTED_COLOR, 22, large=self.large_text)

        title, desc = self.STEPS[self._step]
        bob = int(math.sin(self._time * 2.0) * 5)
        _text(surf, title, WIDTH // 2, 160 + bob, TITLE_COLOR, 38,
              large=self.large_text)

        # Animated bird icon
        bird_y = 280 + bob
        pygame.draw.circle(surf, (250, 210, 70), (WIDTH // 2, bird_y), 22)
        pygame.draw.circle(surf, (200, 160, 20), (WIDTH // 2, bird_y), 22, 2)
        pygame.draw.circle(surf, (255, 255, 255), (WIDTH // 2 + 8, bird_y - 6), 7)
        pygame.draw.circle(surf, (0, 0, 0), (WIDTH // 2 + 9, bird_y - 6), 4)

        for i, line in enumerate(desc.split("\n")):
            _text(surf, line, WIDTH // 2, 330 + i * 34, (200, 215, 240), 24,
                  large=self.large_text)

        # Step dots
        for i in range(len(self.STEPS)):
            col = TITLE_COLOR if i == self._step else MUTED_COLOR
            pygame.draw.circle(surf, col,
                               (WIDTH // 2 - (len(self.STEPS) - 1) * 14 + i * 28,
                                HEIGHT - 140), 6)

        self._next_btn.draw(surf, self.large_text)
        self._skip_btn.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Pause Menu Screen (feature #68)
# ---------------------------------------------------------------------------

class PauseMenuScreen(Screen):
    def __init__(self, large_text: bool = False) -> None:
        super().__init__(large_text)
        cx = WIDTH // 2
        self.buttons = {
            "RESUME":   self._btn(cx, 220, 200, "Resume"),
            "RESTART":  self._btn(cx, 274, 200, "Restart"),
            "SETTINGS": self._btn(cx, 328, 200, "Settings"),
            "MAINMENU": self._btn(cx, 382, 200, "Main Menu",
                                  color=(80, 80, 120)),
            "QUIT":     self._btn(cx, 436, 200, "Quit",
                                  color=(120, 40, 40)),
        }

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        for action, btn in self.buttons.items():
            if btn.handle_event(event):
                return action
        return None

    def draw(self, surf: pygame.Surface) -> None:
        # Semi-transparent overlay over game
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 180))
        surf.blit(overlay, (0, 0))
        _text(surf, "PAUSED", WIDTH // 2, 155, TITLE_COLOR, 50,
              large=self.large_text)
        for btn in self.buttons.values():
            btn.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# Game Over Screen / Score Card (features #47, #50, #67)
# ---------------------------------------------------------------------------

class GameOverScreen(Screen):
    def __init__(self, result: Dict, large_text: bool = False) -> None:
        """result keys: score, best_score, is_new_best, medal, pipes,
        perfects, close_calls, combo_peak, game_time, game_mode,
        lives_remaining, challenge_done, daily_best, session_best."""
        super().__init__(large_text)
        self.result = result
        cx = WIDTH // 2
        self.restart_btn = self._btn(cx, HEIGHT - 100, 200, "Play Again")
        self.menu_btn = self._btn(cx, HEIGHT - 48, 180, "Main Menu",
                                  color=(80, 80, 120))
        self._time = 0.0

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        if self.restart_btn.handle_event(event):
            return "RESTART"
        if self.menu_btn.handle_event(event):
            return "MAINMENU"
        return None

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill(PANEL_BG)
        r = self.result

        # Medal
        medal_name, medal_col = _medal_info(r.get("score", 0))
        bob = int(math.sin(self._time * 3) * 3)
        if medal_name:
            _text(surf, medal_name, WIDTH // 2, 44 + bob, medal_col, 32,
                  large=self.large_text)

        # Score
        _text(surf, str(r.get("score", 0)), WIDTH // 2, 90,
              TITLE_COLOR, 56, large=self.large_text)

        if r.get("is_new_best"):
            col = (255, 220, 50)
            pulse = 0.5 + 0.5 * math.sin(self._time * 6)
            col = tuple(int(c * pulse) for c in (255, 220, 50))
            _text(surf, "★ New Best! ★", WIDTH // 2, 134, col, 28,
                  large=self.large_text)
        else:
            best = r.get("best_score", 0)
            if best:
                _text(surf, f"Best: {best}", WIDTH // 2, 134,
                      MUTED_COLOR, 24, large=self.large_text)

        # Stats grid
        rows = [
            ("Pipes passed",  str(r.get("pipes", 0))),
            ("Perfect passes",str(r.get("perfects", 0))),
            ("Close calls",   str(r.get("close_calls", 0))),
            ("Combo peak",    f"×{r.get('combo_peak', 1)}"),
            ("Daily best",    str(r.get("daily_best", 0))),
            ("Session best",  str(r.get("session_best", 0))),
        ]
        mode = r.get("game_mode", "CLASSIC")
        if mode == "TIME_ATTACK":
            rows.append(("Time", f"{r.get('game_time', 0):.1f}s"))
        elif mode == "SURVIVAL":
            rows.append(("Lives left", str(r.get("lives_remaining", 0))))
        elif mode == "CHALLENGE":
            rows.append(("Objectives", "Done!" if r.get("challenge_done") else "Incomplete"))

        y0 = 162
        row_h = 30
        for label, val in rows:
            if y0 > HEIGHT - 120:
                break
            _text(surf, label, 30, y0, MUTED_COLOR, 20,
                  center=False, large=self.large_text)
            _text(surf, val, WIDTH - 30, y0, (220, 230, 255), 20,
                  center=False, large=self.large_text)
            y0 += row_h

        self.restart_btn.draw(surf, self.large_text)
        self.menu_btn.draw(surf, self.large_text)


# ---------------------------------------------------------------------------
# In-game HUD helpers (not a Screen, drawn directly in main.py)
# ---------------------------------------------------------------------------

def draw_lives_hud(surf: pygame.Surface, lives: int, max_lives: int = 3) -> None:
    """Draw heart icons for Survival mode (feature #40)."""
    for i in range(max_lives):
        col = DANGER_COLOR if i < lives else MUTED_COLOR
        cx = WIDTH - 20 - i * 22
        cy = 15
        pygame.draw.circle(surf, col, (cx - 4, cy - 2), 5)
        pygame.draw.circle(surf, col, (cx + 4, cy - 2), 5)
        pts = [(cx - 9, cy), (cx, cy + 9), (cx + 9, cy)]
        pygame.draw.polygon(surf, col, pts)


def draw_timer_hud(surf: pygame.Surface, time_left: float,
                   total: float = 60.0, large: bool = False) -> None:
    """Draw countdown bar for Time Attack mode (feature #39)."""
    bar_w = WIDTH - 40
    filled = int(bar_w * max(0, time_left) / total)
    pct = time_left / total
    col = (SUCCESS_COLOR if pct > 0.5
           else WARNING_COLOR if pct > 0.25
           else DANGER_COLOR)
    pygame.draw.rect(surf, (40, 50, 70),
                     pygame.Rect(20, HEIGHT - FLOOR_HEIGHT - 14, bar_w, 8),
                     border_radius=4)
    if filled:
        pygame.draw.rect(surf, col,
                         pygame.Rect(20, HEIGHT - FLOOR_HEIGHT - 14, filled, 8),
                         border_radius=4)
    f = _font(20, large)
    lbl = f.render(f"{int(time_left)}s", True, col)
    surf.blit(lbl, lbl.get_rect(topright=(WIDTH - 20, HEIGHT - FLOOR_HEIGHT - 26)))


def draw_powerup_hud(surf: pygame.Surface, ptype: Optional[str],
                     timer: float, max_time: float) -> None:
    """Draw active power-up indicator and duration bar (feature #58)."""
    if not ptype:
        return
    from settings import POWERUP_COLORS, POWERUP_LABELS
    col = POWERUP_COLORS.get(ptype, (200, 200, 200))
    lbl_str = POWERUP_LABELS.get(ptype, "?")
    bar_w = 80
    filled = int(bar_w * min(1, timer / max(0.001, max_time)))

    pygame.draw.rect(surf, (40, 50, 70),
                     pygame.Rect(20, 14, bar_w, 8), border_radius=4)
    if filled:
        pygame.draw.rect(surf, col,
                         pygame.Rect(20, 14, filled, 8), border_radius=4)
    f = _font(18)
    t = f.render(lbl_str, True, col)
    surf.blit(t, (bar_w + 26, 8))


def draw_combo_hud(surf: pygame.Surface, combo: int) -> None:
    """Display current combo multiplier (feature #46)."""
    if combo < 2:
        return
    col = (255, 220, 50) if combo < 3 else (255, 150, 50) if combo < 5 else (255, 80, 80)
    f = _font(28)
    t = f.render(f"×{combo}", True, col)
    surf.blit(t, t.get_rect(topright=(WIDTH - 12, 40)))


def draw_streak_hud(surf: pygame.Surface, streak: int) -> None:
    """Pipe streak counter (feature #48)."""
    if streak < 2:
        return
    f = _font(20)
    t = f.render(f"{streak}🔥", True, (255, 180, 50))
    surf.blit(t, t.get_rect(topright=(WIDTH - 12, 68)))


def draw_speed_hud(surf: pygame.Surface, speed: float,
                   max_speed: float) -> None:
    """Tiny speed bar at bottom (feature #30)."""
    from settings import PIPE_SPEED
    bar_w = 60
    filled = int(bar_w * min(1, (speed - PIPE_SPEED) / max(0.001, max_speed - PIPE_SPEED)))
    rect = pygame.Rect(20, HEIGHT - FLOOR_HEIGHT - 28, bar_w, 5)
    pygame.draw.rect(surf, (40, 50, 70), rect, border_radius=3)
    if filled:
        pygame.draw.rect(surf, WARNING_COLOR,
                         pygame.Rect(rect.x, rect.y, filled, 5), border_radius=3)


def draw_mute_button(surf: pygame.Surface, muted: bool) -> pygame.Rect:
    """Small mute icon in top-right corner (feature #74)."""
    r = pygame.Rect(WIDTH - 34, 4, 28, 28)
    pygame.draw.rect(surf, (40, 50, 70), r, border_radius=6)
    f = _font(20)
    icon = "🔇" if muted else "🔊"
    t = f.render(icon, True, MUTED_COLOR if muted else (200, 220, 255))
    surf.blit(t, t.get_rect(center=r.center))
    return r


def draw_challenge_hud(surf: pygame.Surface, obj_label: str,
                       current: int, target: int) -> None:
    """Show current challenge objective (feature #42)."""
    pct = min(1.0, current / max(1, target))
    _text(surf, obj_label, WIDTH // 2, HEIGHT - FLOOR_HEIGHT - 36,
          SUBTITLE_COLOR, 18)
    bar_w = WIDTH - 80
    bx = 40
    by = HEIGHT - FLOOR_HEIGHT - 22
    pygame.draw.rect(surf, (40, 50, 70),
                     pygame.Rect(bx, by, bar_w, 6), border_radius=3)
    if pct:
        pygame.draw.rect(surf, SUCCESS_COLOR,
                         pygame.Rect(bx, by, int(bar_w * pct), 6), border_radius=3)


def draw_vignette(surf: pygame.Surface, color: tuple, alpha: int) -> None:
    """Screen-edge vignette (used for close-call red pulse, #14)."""
    vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    thickness = 40
    for i in range(thickness):
        a = int(alpha * (thickness - i) / thickness)
        r, g, b = color
        pygame.draw.rect(vig, (r, g, b, a),
                         pygame.Rect(i, i, WIDTH - 2 * i, HEIGHT - 2 * i),
                         1)
    surf.blit(vig, (0, 0))


# ---------------------------------------------------------------------------
# Medal helper
# ---------------------------------------------------------------------------

def _medal_info(score: int) -> tuple:
    if score >= MEDAL_PLATINUM:
        return "✦ PLATINUM ✦", (180, 220, 255)
    elif score >= MEDAL_GOLD:
        return "✦ GOLD ✦", (255, 215, 0)
    elif score >= MEDAL_SILVER:
        return "● SILVER ●", (192, 192, 192)
    elif score >= MEDAL_BRONZE:
        return "● BRONZE ●", (205, 127, 50)
    return "", (0, 0, 0)


def get_medal_color(score: int) -> tuple:
    _, col = _medal_info(score)
    return col
