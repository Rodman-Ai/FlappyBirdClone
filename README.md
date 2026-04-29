# Flappy Bird Clone

A Python/Pygame Flappy Bird clone with object pooling, surface caching, an achievement system, adaptive quality, and web/mobile support via pygbag.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Python 3.8+ required.

## Controls

| Input | Action |
|-------|--------|
| Space / Tap / Click | Flap |
| P | Pause / Resume |
| R | Restart (Game Over screen) |
| F1 | Toggle performance overlay |
| ESC | Quit |

## Mobile & Web

The game builds to WebAssembly with [pygbag](https://pygame-web.github.io/) and runs in any browser, including mobile. Touch (`tap`) is handled identically to mouse click.

```bash
pip install pygbag
python -m pygbag main.py
# Open http://localhost:8000 on any device
```

## Features

### Gameplay
- Realistic physics: gravity, wing drag, terminal velocity
- Smooth bird tilt and wing animation
- Pause/resume (P key or tap)

### Achievements
- 14 achievements across four categories: Progression, Skill, Persistence, Hidden
- Persistent across sessions via `achievements.json`
- In-game unlock notifications

### Performance
- **Object pool** — pipes reused, zero per-frame allocation
- **Surface cache** — pipe and bird surfaces pre-rendered
- **Broad-phase collision** — only pipes in X range are tested
- **Cached background** — static sky + clouds rendered once
- **Adaptive quality** — effects scaled automatically to hold 60 FPS
- **F1 overlay** — real-time FPS, memory, CPU, cache stats

## Project Structure

```
FlappyBirdClone/
├── main.py              Async game loop and entry point
├── sprites.py           Bird, PipePair, PipePool, collision helpers, surface cache
├── settings.py          All numeric constants
├── game_stats.py        Achievements, statistics, configuration
├── performance.py       EfficiencyManager, adaptive quality, renderer
├── requirements.txt     Desktop dependencies
├── requirements-web.txt Web/mobile build dependencies
├── CLAUDE.md            Codebase guide for Claude Code
└── docs/
    ├── README.md            Complete project wiki
    ├── API-Reference.md     Class and function documentation
    ├── Development-Guide.md Architecture and contributing guide
    ├── Performance-Guide.md Optimization details and bottleneck guide
    └── Achievement-Guide.md Full achievement list and unlock conditions
```

## Configuration

`game_config.json` is created automatically. Key options:

```json
{
  "show_fps": false,
  "show_performance": false,
  "difficulty": "normal"
}
```

## Documentation

- [Complete Wiki](docs/README.md)
- [API Reference](docs/API-Reference.md)
- [Development Guide](docs/Development-Guide.md)
- [Performance Guide](docs/Performance-Guide.md)
- [Achievement Guide](docs/Achievement-Guide.md)

## System Requirements

- **Desktop:** Python 3.8+, any modern OS
- **Web/Mobile:** Any browser with WebAssembly support (Chrome, Firefox, Safari, Edge)
- **Memory:** ~50–80 MB at runtime
