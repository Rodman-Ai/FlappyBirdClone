# audio.py — synthesized sound and music manager (features #1-6)
import pygame
import math
import struct
import random
from typing import Dict, Optional

from settings import DEFAULT_SFX_VOLUME, DEFAULT_MUSIC_VOLUME


# ---------------------------------------------------------------------------
# PCM synthesis helpers
# ---------------------------------------------------------------------------

def _gen_sine(freq: float, duration: float, volume: float = 0.4,
              sample_rate: int = 44100) -> bytes:
    """Sine wave with linear attack/decay envelope."""
    n = int(sample_rate * duration)
    attack = int(sample_rate * 0.01)
    decay = int(sample_rate * 0.05)
    data = bytearray(n * 4)
    for i in range(n):
        env = 1.0
        if i < attack:
            env = i / attack
        elif i > n - decay:
            env = (n - i) / decay
        sample = int(volume * 32767 * env * math.sin(2 * math.pi * freq * i / sample_rate))
        sample = max(-32768, min(32767, sample))
        struct.pack_into('<hh', data, i * 4, sample, sample)
    return bytes(data)


def _gen_sweep(f0: float, f1: float, duration: float,
               volume: float = 0.4, sample_rate: int = 44100) -> bytes:
    """Frequency sweep (linear) with bell-shaped amplitude envelope."""
    n = int(sample_rate * duration)
    data = bytearray(n * 4)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        env = math.sin(math.pi * t)
        sample = int(volume * 32767 * env * math.sin(phase))
        sample = max(-32768, min(32767, sample))
        struct.pack_into('<hh', data, i * 4, sample, sample)
        phase += 2 * math.pi * freq / sample_rate
    return bytes(data)


def _gen_noise(duration: float, volume: float = 0.35,
               sample_rate: int = 44100) -> bytes:
    """White noise with fast exponential decay (death/collision)."""
    n = int(sample_rate * duration)
    data = bytearray(n * 4)
    rng = random.Random(42)
    for i in range(n):
        env = math.exp(-6 * i / n)
        sample = int(volume * 32767 * env * rng.uniform(-1, 1))
        sample = max(-32768, min(32767, sample))
        struct.pack_into('<hh', data, i * 4, sample, sample)
    return bytes(data)


def _concat(*buffers: bytes) -> bytes:
    return b"".join(buffers)


# ---------------------------------------------------------------------------
# AudioManager
# ---------------------------------------------------------------------------

class AudioManager:
    """Centralised sound-effects and music controller.

    Sounds are synthesized from PCM at initialisation time — no external
    audio files required, ensuring the game works on web builds too.
    """

    def __init__(self) -> None:
        self._ready = False
        self._sfx_volume = DEFAULT_SFX_VOLUME
        self._music_volume = DEFAULT_MUSIC_VOLUME
        self._muted = False
        self._sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Call once after pygame.init(). Safe to call multiple times."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._ready = True
            self._build_sounds()
        except Exception as exc:
            print(f"[audio] init failed ({exc}); running silent")
            self._ready = False

    def _build_sounds(self) -> None:
        """Synthesize all sound effects into pygame.mixer.Sound objects."""
        recipes: Dict[str, bytes] = {
            # Core gameplay (features #1-3)
            "flap":        _gen_sweep(320, 640, 0.07, 0.28),
            "score":       _gen_sweep(520, 920, 0.11, 0.32),
            "death":       _gen_noise(0.38, 0.40),
            # Meta (features #4)
            "achievement": _concat(_gen_sweep(420, 840, 0.20, 0.38),
                                   _gen_sweep(600, 1100, 0.18, 0.35)),
            # Collectibles / power-ups
            "coin":        _gen_sweep(720, 1120, 0.09, 0.28),
            "powerup":     _concat(_gen_sweep(300, 700, 0.12, 0.30),
                                   _gen_sweep(500, 900, 0.10, 0.28)),
            "shield_hit":  _gen_sweep(600, 200, 0.18, 0.35),
            # Countdown / UI (features #34, #66)
            "countdown":   _gen_sine(440, 0.14, 0.38),
            "go":          _gen_sine(660, 0.22, 0.42),
            "ui_click":    _gen_sine(800, 0.05, 0.18),
            # Scoring milestones
            "medal":       _concat(_gen_sweep(480, 960, 0.22, 0.35),
                                   _gen_sweep(600, 1200, 0.20, 0.32)),
            "new_best":    _concat(_gen_sweep(400, 800, 0.18, 0.35),
                                   _gen_sweep(700, 1400, 0.25, 0.40),
                                   _gen_sweep(900, 1800, 0.20, 0.35)),
            # Survival (feature #40)
            "life_lost":   _gen_sweep(400, 150, 0.22, 0.38),
            "life_gain":   _gen_sweep(380, 760, 0.18, 0.35),
            # Combo
            "combo":       _gen_sweep(550, 1000, 0.09, 0.30),
        }
        for name, pcm in recipes.items():
            try:
                snd = pygame.mixer.Sound(buffer=pcm)
                snd.set_volume(self._sfx_volume)
                self._sounds[name] = snd
            except Exception as exc:
                print(f"[audio] could not create '{name}': {exc}")
                self._sounds[name] = None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play(self, name: str) -> None:
        """Play a named SFX; silently ignored if audio is unavailable."""
        if not self._ready or self._muted:
            return
        snd = self._sounds.get(name)
        if snd:
            snd.play()

    def play_music(self) -> None:
        """Start looping ambient background music (feature #5).

        We generate a short ambient drone as a raw buffer and loop it via
        pygame.mixer.music — no external files needed.
        """
        if not self._ready or self._muted:
            return
        # Use a quiet ambient chord (root + 5th) as a looping tone
        try:
            import io
            chord = _concat(
                _gen_sine(130, 4.0, 0.08),
                _gen_sine(195, 4.0, 0.06),
                _gen_sine(260, 4.0, 0.04),
            )
            # Combine additively
            n = len(chord) // 3
            combined = bytearray(n)
            for i in range(0, n, 4):
                s1 = struct.unpack_from('<h', chord,         i)[0]
                s2 = struct.unpack_from('<h', chord,     n + i)[0]
                s3 = struct.unpack_from('<h', chord, 2 * n + i)[0]
                s = max(-32768, min(32767, s1 + s2 + s3))
                struct.pack_into('<hh', combined, i, s, s)
            buf = io.BytesIO(bytes(combined))
            pygame.mixer.music.load(buf)
            pygame.mixer.music.set_volume(self._music_volume if not self._muted else 0)
            pygame.mixer.music.play(-1)
        except Exception as exc:
            print(f"[audio] music failed: {exc}")

    def stop_music(self) -> None:
        if self._ready:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Volume control (features #6, #74)
    # ------------------------------------------------------------------

    def set_sfx_volume(self, vol: float) -> None:
        self._sfx_volume = max(0.0, min(1.0, vol))
        if not self._muted:
            for snd in self._sounds.values():
                if snd:
                    snd.set_volume(self._sfx_volume)

    def set_music_volume(self, vol: float) -> None:
        self._music_volume = max(0.0, min(1.0, vol))
        if not self._muted:
            try:
                pygame.mixer.music.set_volume(self._music_volume)
            except Exception:
                pass

    def set_muted(self, muted: bool) -> None:
        """One-click mute/unmute all audio (feature #74)."""
        self._muted = muted
        effective_sfx = 0.0 if muted else self._sfx_volume
        effective_mus = 0.0 if muted else self._music_volume
        for snd in self._sounds.values():
            if snd:
                snd.set_volume(effective_sfx)
        try:
            pygame.mixer.music.set_volume(effective_mus)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def sfx_volume(self) -> float:
        return self._sfx_volume

    @property
    def music_volume(self) -> float:
        return self._music_volume

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def ready(self) -> bool:
        return self._ready
