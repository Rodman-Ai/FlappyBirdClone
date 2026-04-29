# Achievement Guide

Achievements are saved to `achievements.json` in the project root. They persist across sessions. Hidden achievements are not shown until unlocked.

---

## Progression achievements

| Name | Description | Unlock condition |
|------|-------------|-----------------|
| First Flight | Complete your first game | Play 1 game |
| Baby Steps | Pass through 5 pipes | Score ≥ 5 in a single game |
| Getting Good | Score 10 points | Score ≥ 10 |
| Decent Pilot | Score 25 points | Score ≥ 25 |
| Skilled Flyer | Score 50 points | Score ≥ 50 |
| Ace Pilot | Score 100 points | Score ≥ 100 |

---

## Skill achievements

| Name | Description | Unlock condition |
|------|-------------|-----------------|
| Precision Pilot | Pass 10 pipes through the centre | 10 cumulative perfect passes (centre 30 % of gap) |
| Close Call King | Have 25 near misses | 25 cumulative close calls (< 20 px from pipe edge) |
| Efficient Flyer | Score 20+ with fewer than 50 flaps | Score ≥ 20 and flap count < 50 in a single game |

---

## Persistence achievements

| Name | Description | Unlock condition |
|------|-------------|-----------------|
| Dedicated | Play 50 games | 50 total games played |
| Marathon Runner | Survive for 60 seconds | Stay alive 60 s in a single game |
| Century Club | Pass 100 total pipes | 100 cumulative pipes passed |

---

## Hidden achievements

These are not shown until unlocked.

| Name | Description | Unlock condition |
|------|-------------|-----------------|
| Crash Test Dummy | Die 100 times | 100 total deaths |
| Button Masher | Flap 1 000 times total | 1 000 cumulative flaps |

---

## How achievements are detected

`AchievementManager.check_achievements()` is called on every game-over. It receives the current `GameStatistics` object plus the just-finished game's `score`, `flap_count`, and `game_time`. Each achievement maps to a numeric value that is compared against its `target`.

## Adding achievements

See [Development Guide — Add a new achievement](Development-Guide.md#add-a-new-achievement).
