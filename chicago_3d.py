"""Chicago 3D Train Simulation - L Train elevated rail system"""
import pygame
import math
import sys
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

SCREEN_W, SCREEN_H = 1200, 800
FPS = 60
TITLE = "Chicago 3D - L Train Simulation"

SKY_COLOR = (100, 160, 210)
HORIZON_COLOR = (180, 210, 230)
GROUND_COLOR = (70, 90, 65)
ROAD_COLOR = (55, 55, 55)
WATER_COLOR = (20, 60, 140)
TRACK_COLOR = (90, 70, 50)
PILLAR_COLOR = (110, 95, 75)

BUILDING_PALETTES = [
    (175, 185, 195),
    (160, 168, 180),
    (195, 190, 178),
    (170, 178, 188),
    (185, 178, 168),
]
GLASS_PALETTES = [
    (80, 130, 190),
    (90, 150, 200),
    (70, 140, 185),
    (85, 145, 195),
]

LINE_COLORS = {
    'brown': (139, 90, 43),
    'red':   (204, 51, 51),
    'blue':  (51, 102, 204),
    'orange':(220, 130, 30),
    'green': (50, 175, 50),
    'pink':  (210, 120, 170),
    'purple':(140, 50, 190),
}

BLOCK = 100
EL_H = 45  # elevated track height


# ---------------------------------------------------------------------------
# 3D Math
# ---------------------------------------------------------------------------

def rot_y(x, y, z, a):
    c, s = math.cos(a), math.sin(a)
    return x * c + z * s, y, -x * s + z * c


def rot_x(x, y, z, a):
    c, s = math.cos(a), math.sin(a)
    return x, y * c - z * s, y * s + z * c


def project(x, y, z, cx, cy, cz, yaw, pitch, fov, sw, sh):
    x -= cx; y -= cy; z -= cz
    x, y, z = rot_y(x, y, z, -yaw)
    x, y, z = rot_x(x, y, z, -pitch)
    if z < 1:
        return None
    return (x / z * fov + sw / 2, -y / z * fov + sh / 2)


# ---------------------------------------------------------------------------
# Scene objects
# ---------------------------------------------------------------------------

@dataclass
class Building:
    x: float
    z: float
    w: float
    d: float
    h: float
    color: tuple
    glass: bool = False

    @property
    def corners(self):
        x0, x1 = self.x - self.w / 2, self.x + self.w / 2
        z0, z1 = self.z - self.d / 2, self.z + self.d / 2
        return [
            (x0, 0,      z0), (x1, 0,      z0),
            (x1, self.h, z0), (x0, self.h, z0),
            (x0, 0,      z1), (x1, 0,      z1),
            (x1, self.h, z1), (x0, self.h, z1),
        ]

    FACES = [
        ([0, 1, 2, 3], 0.75, 'side'),
        ([5, 4, 7, 6], 0.50, 'side'),
        ([4, 0, 3, 7], 0.60, 'side'),
        ([1, 5, 6, 2], 0.85, 'side'),
        ([3, 2, 6, 7], 1.00, 'top'),
    ]


@dataclass
class Track:
    waypoints: List[Tuple[float, float, float]]
    loop: bool = True

    @property
    def length(self):
        pts = self.waypoints
        total = 0.0
        n = len(pts) - (0 if self.loop else 1)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            dx, dy, dz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            total += math.sqrt(dx*dx + dy*dy + dz*dz)
        return total

    def pos_at(self, dist):
        pts = self.waypoints
        n = len(pts)
        total = 0.0
        steps = n if self.loop else n - 1
        for i in range(steps):
            a = pts[i]
            b = pts[(i + 1) % n]
            dx, dy, dz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            seg = math.sqrt(dx*dx + dy*dy + dz*dz)
            if seg == 0:
                continue
            if total + seg >= dist:
                t = (dist - total) / seg
                pos = (a[0]+dx*t, a[1]+dy*t, a[2]+dz*t)
                heading = math.atan2(dx, dz)
                return pos, heading
            total += seg
        last = pts[-1]
        prev = pts[-2]
        dx, dz = last[0]-prev[0], last[2]-prev[2]
        return last, math.atan2(dx, dz)


@dataclass
class Train:
    track: Track
    color: tuple
    name: str
    n_cars: int = 5
    car_gap: float = 22.0
    speed: float = 130.0
    t: float = 0.0

    def update(self, dt):
        L = self.track.length
        if L > 0:
            self.t = (self.t + self.speed * dt / L) % 1.0

    def car_positions(self):
        L = self.track.length
        results = []
        for i in range(self.n_cars):
            dist = (self.t * L - i * self.car_gap) % L
            results.append(self.track.pos_at(dist))
        return results


# ---------------------------------------------------------------------------
# City builder
# ---------------------------------------------------------------------------

def build_city():
    rng = random.Random(7)
    buildings = []

    landmarks = [
        (0,    0,    60, 60, 442, (70, 120, 175), True),   # Willis Tower
        (190, -80,   50, 50, 344, (175, 185, 195), False), # Hancock-ish
        (110, 110,   45, 45, 346, (80, 140, 195), True),   # Aon Center
        (-120, 60,   52, 52, 298, (195, 190, 175), False), # Trump
        (155, 195,   40, 40, 261, (85, 145, 200), True),
        (-200,-120,  58, 42, 275, (160, 170, 185), False),
        (295, 95,    38, 38, 198, (90, 150, 200), True),
        (-60, -200,  44, 44, 225, (180, 188, 197), False),
        (280, -200,  35, 50, 185, (80, 135, 192), True),
    ]
    for lm in landmarks:
        buildings.append(Building(*lm))

    for bx in range(-8, 9):
        for bz in range(-8, 9):
            wx, wz = bx * BLOCK, bz * BLOCK
            if any(abs(wx - l[0]) < 90 and abs(wz - l[1]) < 90 for l in landmarks):
                continue
            w = rng.randint(38, 78)
            d = rng.randint(38, 78)
            h = rng.randint(30, 230)
            glass = rng.random() < 0.28
            if glass:
                color = rng.choice(GLASS_PALETTES)
                color = tuple(max(0, min(255, c + rng.randint(-15, 15))) for c in color)
            else:
                color = rng.choice(BUILDING_PALETTES)
                color = tuple(max(0, min(255, c + rng.randint(-20, 20))) for c in color)
            buildings.append(Building(wx, wz, w, d, h, color, glass))

    return buildings


def build_tracks():
    EH = EL_H
    tracks = {}

    # The Loop - rectangular elevated route downtown
    tracks['loop'] = Track([
        (-260, EH, -310), (260, EH, -310),
        (260, EH,  310), (-260, EH,  310),
    ], loop=True)

    # Red Line - N/S through the loop
    tracks['red'] = Track([
        (0, EH, -900), (0, EH, -310),
        (0, EH,  310), (0, EH,  900),
    ], loop=False)

    # Blue Line - E/W
    tracks['blue'] = Track([
        (-900, EH, 0), (-260, EH, 0),
        ( 260, EH, 0), ( 900, EH, 0),
    ], loop=False)

    # Orange Line - SW diagonal (to Midway)
    tracks['orange'] = Track([
        (-260, EH, 310), (-380, EH, 510),
        (-500, EH, 720), (-610, EH, 950),
    ], loop=False)

    # Green Line - E to Museum Campus area
    tracks['green'] = Track([
        (260, EH, -310), (480, EH, -310),
        (700, EH, -310), (950, EH, -530),
    ], loop=False)

    # Pink Line - SW
    tracks['pink'] = Track([
        (-260, EH, 0), (-450, EH, 150),
        (-650, EH, 300), (-850, EH, 500),
    ], loop=False)

    # Purple/Brown extension north
    tracks['purple'] = Track([
        (-260, EH, -310), (-260, EH, -550),
        (-260, EH, -800), (-260, EH, -1000),
    ], loop=False)

    return tracks


def build_trains(tracks):
    trains = []

    # Loop - 3 Brown line trains circling
    for i in range(3):
        tr = Train(tracks['loop'], LINE_COLORS['brown'], 'Brown/Loop', n_cars=6, speed=110)
        tr.t = i / 3.0
        trains.append(tr)

    # Red - 2 trains
    for i in range(2):
        tr = Train(tracks['red'], LINE_COLORS['red'], 'Red', n_cars=8, speed=155)
        tr.t = i / 2.0
        trains.append(tr)

    # Blue - 2 trains
    for i in range(2):
        tr = Train(tracks['blue'], LINE_COLORS['blue'], 'Blue', n_cars=8, speed=155)
        tr.t = i / 2.0
        trains.append(tr)

    # Orange
    tr = Train(tracks['orange'], LINE_COLORS['orange'], 'Orange', n_cars=6, speed=120)
    trains.append(tr)

    # Green
    tr = Train(tracks['green'], LINE_COLORS['green'], 'Green', n_cars=6, speed=120)
    trains.append(tr)

    # Pink
    tr = Train(tracks['pink'], LINE_COLORS['pink'], 'Pink', n_cars=5, speed=110)
    trains.append(tr)

    # Purple
    tr = Train(tracks['purple'], LINE_COLORS['purple'], 'Purple', n_cars=5, speed=110)
    trains.append(tr)

    return trains


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class Camera:
    def __init__(self):
        self.x, self.y, self.z = 0.0, 420.0, -850.0
        self.yaw = 0.0
        self.pitch = 0.52
        self.fov = 640.0

    def project(self, x, y, z):
        return project(x, y, z, self.x, self.y, self.z,
                       self.yaw, self.pitch, self.fov, SCREEN_W, SCREEN_H)


def shade(color, brightness):
    return tuple(min(255, max(0, int(c * brightness))) for c in color)


def face_visible(pts2d):
    if len(pts2d) < 3:
        return False
    ax, ay = pts2d[1][0] - pts2d[0][0], pts2d[1][1] - pts2d[0][1]
    bx, by = pts2d[2][0] - pts2d[0][0], pts2d[2][1] - pts2d[0][1]
    return ax * by - ay * bx > 0


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.cam = Camera()
        self._sky_surf = self._make_sky()

    def _make_sky(self):
        surf = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(SKY_COLOR[0] * (1 - t) + HORIZON_COLOR[0] * t)
            g = int(SKY_COLOR[1] * (1 - t) + HORIZON_COLOR[1] * t)
            b = int(SKY_COLOR[2] * (1 - t) + HORIZON_COLOR[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_W, y))
        return surf

    def draw_sky(self):
        self.screen.blit(self._sky_surf, (0, 0))

    def draw_ground(self):
        S = 2500
        corners_ground = [(-S, 0, -S), (S, 0, -S), (S, 0, S), (-S, 0, S)]
        pts = [self.cam.project(*c) for c in corners_ground]
        valid = [p for p in pts if p]
        if len(valid) >= 3:
            pygame.draw.polygon(self.screen, GROUND_COLOR, pts if all(pts) else valid)

        # Lake Michigan (east)
        lake = [(350, 0, -S), (S+500, 0, -S), (S+500, 0, S), (350, 0, S)]
        lpts = [self.cam.project(*c) for c in lake]
        if all(lpts):
            pygame.draw.polygon(self.screen, WATER_COLOR, lpts)

    def draw_roads(self):
        # Draw a simple grid of roads
        for i in range(-8, 9):
            # E-W roads
            a = self.cam.project(i * BLOCK - 15, 1, -1000)
            b = self.cam.project(i * BLOCK - 15, 1,  1000)
            c = self.cam.project(i * BLOCK + 15, 1,  1000)
            d = self.cam.project(i * BLOCK + 15, 1, -1000)
            if a and b and c and d:
                pygame.draw.polygon(self.screen, ROAD_COLOR, [a, b, c, d])
            # N-S roads
            a = self.cam.project(-1000, 1, i * BLOCK - 15)
            b = self.cam.project( 1000, 1, i * BLOCK - 15)
            c = self.cam.project( 1000, 1, i * BLOCK + 15)
            d = self.cam.project(-1000, 1, i * BLOCK + 15)
            if a and b and c and d:
                pygame.draw.polygon(self.screen, ROAD_COLOR, [a, b, c, d])

    def draw_building(self, b: Building):
        corners = b.corners
        proj = [self.cam.project(*c) for c in corners]

        depth_key = (b.x - self.cam.x)**2 + (b.z - self.cam.z)**2

        faces = []
        for idxs, brightness, kind in Building.FACES:
            pts2d = [proj[i] for i in idxs]
            if any(p is None for p in pts2d):
                continue
            if not face_visible(pts2d):
                continue
            avg_depth = sum((corners[i][0]-self.cam.x)**2 + (corners[i][2]-self.cam.z)**2
                            for i in idxs) / len(idxs)
            c = shade(b.color, brightness)
            faces.append((avg_depth, pts2d, c, kind, brightness))

        faces.sort(key=lambda f: -f[0])
        for _, pts2d, c, kind, brightness in faces:
            pygame.draw.polygon(self.screen, c, pts2d)
            if b.glass and kind == 'side' and brightness > 0.6:
                self._draw_windows(pts2d, c)

    def _draw_windows(self, pts2d, face_color):
        xs = [p[0] for p in pts2d]
        ys = [p[1] for p in pts2d]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w, h = max_x - min_x, max_y - min_y
        if w < 8 or h < 8:
            return
        rows = max(2, int(h / 14))
        cols = max(2, int(w / 9))
        wc = (min(255, face_color[0] + 40), min(255, face_color[1] + 35),
              min(255, face_color[2] + 25))
        for r in range(1, rows):
            for c in range(1, cols):
                wx = int(min_x + c * w / cols)
                wy = int(min_y + r * h / rows)
                pygame.draw.rect(self.screen, wc, (wx - 2, wy - 2, 4, 3))

    def draw_track(self, track: Track):
        pts = track.waypoints
        n = len(pts)
        steps = n if track.loop else n - 1

        # Rails (two parallel lines)
        for offset in (-4, 4):
            prev_p = None
            for i in range(steps + 1):
                wp = pts[i % n]
                # Offset perpendicular to track direction
                next_wp = pts[(i + 1) % n]
                dx = next_wp[0] - wp[0]
                dz = next_wp[2] - wp[2]
                L = math.sqrt(dx*dx + dz*dz)
                if L > 0:
                    ox, oz = -dz/L * offset, dx/L * offset
                else:
                    ox, oz = 0, 0
                p = self.cam.project(wp[0]+ox, wp[1], wp[2]+oz)
                if p and prev_p:
                    pygame.draw.line(self.screen, TRACK_COLOR,
                                     (int(prev_p[0]), int(prev_p[1])),
                                     (int(p[0]), int(p[1])), 2)
                prev_p = p

        # Tie beams and support pillars
        for i in range(steps):
            wp = pts[i]
            next_wp = pts[(i + 1) % n]
            # Tie at midpoint
            mx = (wp[0] + next_wp[0]) / 2
            my = wp[1]
            mz = (wp[2] + next_wp[2]) / 2
            pt = self.cam.project(mx, my, mz)
            pb = self.cam.project(mx, 0, mz)
            if pt and pb:
                pygame.draw.line(self.screen, PILLAR_COLOR,
                                 (int(pt[0]), int(pt[1])),
                                 (int(pb[0]), int(pb[1])), 3)

    def draw_train_car(self, pos, heading, color):
        x, y, z = pos
        cw, ch, cl = 10, 13, 18
        cos_h = math.cos(heading)
        sin_h = math.sin(heading)

        local = [
            (-cw/2, 0,   -cl/2), (cw/2, 0,   -cl/2),
            (cw/2,  ch,  -cl/2), (-cw/2, ch, -cl/2),
            (-cw/2, 0,    cl/2), (cw/2, 0,    cl/2),
            (cw/2,  ch,   cl/2), (-cw/2, ch,  cl/2),
        ]
        world = []
        for lx, ly, lz in local:
            wx = x + lx * cos_h + lz * sin_h
            wy = y + ly
            wz = z - lx * sin_h + lz * cos_h
            world.append((wx, wy, wz))

        proj = [self.cam.project(*c) for c in world]

        car_faces = [
            ([0, 1, 2, 3], 0.80),
            ([5, 4, 7, 6], 0.55),
            ([4, 0, 3, 7], 0.65),
            ([1, 5, 6, 2], 0.90),
            ([3, 2, 6, 7], 1.00),
        ]
        for idxs, br in car_faces:
            pts2d = [proj[i] for i in idxs]
            if any(p is None for p in pts2d):
                continue
            if not face_visible(pts2d):
                continue
            pygame.draw.polygon(self.screen, shade(color, br), pts2d)
            pygame.draw.polygon(self.screen, shade(color, br * 0.6), pts2d, 1)

    def render(self, buildings, tracks, trains):
        self.draw_sky()
        self.draw_ground()
        self.draw_roads()

        # Sort buildings back-to-front
        cam = self.cam
        sorted_blds = sorted(buildings,
                             key=lambda b: -((b.x-cam.x)**2 + (b.z-cam.z)**2))
        for b in sorted_blds:
            self.draw_building(b)

        for track in tracks:
            self.draw_track(track)

        # Collect all train cars with depth for sorting
        all_cars = []
        for train in trains:
            for pos, heading in train.car_positions():
                depth = (pos[0]-cam.x)**2 + (pos[2]-cam.z)**2
                all_cars.append((depth, pos, heading, train.color))
        all_cars.sort(key=lambda c: -c[0])
        for depth, pos, heading, color in all_cars:
            self.draw_train_car(pos, heading, color)


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

def draw_hud(screen, cam, fps):
    font_sm = pygame.font.SysFont('Arial', 13)
    font_lg = pygame.font.SysFont('Arial', 19, bold=True)

    # Shadow + title
    title = font_lg.render("Chicago 3D — L Train Simulation", True, (0, 0, 0))
    screen.blit(title, (12, 12))
    title = font_lg.render("Chicago 3D — L Train Simulation", True, (255, 255, 255))
    screen.blit(title, (10, 10))

    controls = [
        "WASD / Arrows : Pan",
        "Q / E         : Up / Down",
        "Mouse drag    : Orbit",
        "Scroll wheel  : Zoom",
        "ESC           : Quit",
    ]
    for i, text in enumerate(controls):
        s = font_sm.render(text, True, (30, 30, 30))
        screen.blit(s, (12, 36 + i * 18))
        s = font_sm.render(text, True, (220, 220, 220))
        screen.blit(s, (10, 34 + i * 18))

    # Legend
    legend = [
        ("Brown / Loop",  LINE_COLORS['brown']),
        ("Red Line",      LINE_COLORS['red']),
        ("Blue Line",     LINE_COLORS['blue']),
        ("Orange Line",   LINE_COLORS['orange']),
        ("Green Line",    LINE_COLORS['green']),
        ("Pink Line",     LINE_COLORS['pink']),
        ("Purple Line",   LINE_COLORS['purple']),
    ]
    lx, ly = SCREEN_W - 155, 12
    for name, col in legend:
        pygame.draw.rect(screen, col, (lx, ly, 14, 14))
        pygame.draw.rect(screen, (200, 200, 200), (lx, ly, 14, 14), 1)
        s = font_sm.render(name, True, (220, 220, 220))
        screen.blit(s, (lx + 18, ly))
        ly += 20

    fps_s = font_sm.render(f"FPS: {fps:.0f}", True, (180, 255, 180))
    screen.blit(fps_s, (SCREEN_W - 80, SCREEN_H - 22))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    buildings = build_city()
    track_map = build_tracks()
    tracks = list(track_map.values())
    trains = build_trains(track_map)
    renderer = Renderer(screen)
    cam = renderer.cam

    drag = False
    last_mouse = (0, 0)

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                drag = True
                last_mouse = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drag = False
            elif event.type == pygame.MOUSEMOTION and drag:
                dx, dy = event.pos[0] - last_mouse[0], event.pos[1] - last_mouse[1]
                cam.yaw += dx * 0.005
                cam.pitch = max(0.1, min(1.45, cam.pitch + dy * 0.005))
                last_mouse = event.pos
            elif event.type == pygame.MOUSEWHEEL:
                cam.fov = max(200, min(1400, cam.fov + event.y * 35))

        keys = pygame.key.get_pressed()
        spd = 9.0
        sy, cy = math.sin(cam.yaw), math.cos(cam.yaw)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            cam.x += sy * spd; cam.z += cy * spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            cam.x -= sy * spd; cam.z -= cy * spd
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            cam.x -= cy * spd; cam.z += sy * spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            cam.x += cy * spd; cam.z -= sy * spd
        if keys[pygame.K_q]:
            cam.y += spd
        if keys[pygame.K_e]:
            cam.y -= spd

        for train in trains:
            train.update(dt)

        renderer.render(buildings, tracks, trains)
        draw_hud(screen, cam, clock.get_fps())
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
