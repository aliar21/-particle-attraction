import pygame
import json
import random
import math
import os


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Нормализация значений, которые могут быть списками в JSON
    if isinstance(cfg.get("background_color"), list):
        cfg["background_color"] = tuple(cfg["background_color"])
    if isinstance(cfg.get("particle_color"), list):
        cfg["particle_color"] = tuple(cfg["particle_color"])
    cfg["sample_step"] = max(1, int(cfg.get("sample_step", 3)))
    print("[cfg] loaded", path)
    return cfg


class Particle:
    def __init__(self, start_x, start_y, target_x, target_y, size, color):
        self.x = float(start_x)
        self.y = float(start_y)

        self.target_x = float(target_x)
        self.target_y = float(target_y)

        self.size = int(size)
        self.color = tuple(color)

        self.vx = random.uniform(-1.0, 1.0)
        self.vy = random.uniform(-1.0, 1.0)

    def update(self, mouse_pos, cfg, attraction_strength=1.0, jitter=0.0):
        mx, my = mouse_pos

        # Притяжение к цели
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy) + 1e-6
        base_force = cfg.get("gravity_strength", 0.2)
        force = base_force * attraction_strength

        # Добавляем притяжение пропорциональное направлению
        self.vx += (dx / dist) * force
        self.vy += (dy / dist) * force

        # Отталкивание от мыши
        mdx = self.x - mx
        mdy = self.y - my
        mdist_sq = mdx * mdx + mdy * mdy
        radius = cfg.get("mouse_repulsion_radius", 80)
        if mdist_sq < (radius * radius) and mdist_sq > 0:
            mdist = math.sqrt(mdist_sq)
            rep_force = cfg.get("mouse_repulsion_force", 2.5)
            # сила мягко уменьшается с расстоянием
            f = rep_force * (1.0 - (mdist / radius))
            nx = mdx / (mdist + 1e-6)
            ny = mdy / (mdist + 1e-6)
            self.vx += nx * f
            self.vy += ny * f

        # случайное дрожание
        if jitter > 0:
            self.vx += random.uniform(-jitter, jitter)
            self.vy += random.uniform(-jitter, jitter)

        # Дампинг
        self.vx *= 0.92
        self.vy *= 0.92

        # Обновление позиции
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.size)


def load_image_points(cfg):
    print("[img] trying to load:", cfg["image_path"])

    img = pygame.image.load(cfg["image_path"]).convert_alpha()
    print("[img] loaded image with pygame")
    print("[img] surface size:", img.get_width(), "x", img.get_height())

    points = []
    step = 3  # уменьшает количество частиц

    for y in range(0, img.get_height(), step):
        for x in range(0, img.get_width(), step):
            color = img.get_at((x, y))

            # Берем только темные пиксели текста
            if color.a > 0 and (color.r + color.g + color.b) < 600:
                points.append((x, y))

    print(f"[img] points found: {len(points)} (step={step})")
    return points, img.get_width(), img.get_height()
# -----------------------------
# CREATE PARTICLE SYSTEM
# -----------------------------
def create_particle_system_from_image(cfg):
    points, img_w, img_h = load_image_points(cfg)

    screen_w = cfg["window_width"]
    screen_h = cfg["window_height"]

    # Центрируем текст по экрану
    offset_x = (screen_w - img_w) // 2
    offset_y = (screen_h - img_h) // 2

    particles = []
    for (px, py) in points:
        sx = random.randint(0, screen_w)
        sy = random.randint(0, screen_h)
        tx = px + offset_x
        ty = py + offset_y
        p = Particle(sx, sy, tx, ty, cfg["particle_size"], cfg["particle_color"])
        particles.append(p)

    print(f"[system] created {len(particles)} particles")
    return particles


def main():
    cfg = load_config("config.json")

    pygame.init()
    screen = pygame.display.set_mode((cfg["window_width"], cfg["window_height"]))
    pygame.display.set_caption("Particle Text (controls: C clear, UP/DOWN gravity, T toggle trails)")
    clock = pygame.time.Clock()

    # создаём частицы
    particles = create_particle_system_from_image(cfg)

    attraction_strength = 1.0   # множитель притяжения, изменяется клавишами UP/DOWN
    show_trails = True          # можно переключать клавишей T
    trail_alpha = 40            # прозрачность слоя следов (0..255). меньше = длиннее следы
    jitter_amount = 0.0         # случайный шум
    # создаём поверхность для следов
    trail_surface = pygame.Surface((cfg["window_width"], cfg["window_height"]), pygame.SRCALPHA)
    trail_surface.fill((0, 0, 0, 0))  # полностью прозрачная

    print("[main] starting loop. Controls: C clear | UP/DOWN gravity | T toggle trails")

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Обработка клавиш: очистка и изменение притяжения, переключение следов
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    particles.clear()
                    print("[input] particles cleared")

                if event.key == pygame.K_UP:
                    attraction_strength += 0.1
                    print(f"[input] attraction_strength -> {attraction_strength:.2f}")

                if event.key == pygame.K_DOWN:
                    attraction_strength = max(0.1, attraction_strength - 0.1)
                    print(f"[input] attraction_strength -> {attraction_strength:.2f}")

                if event.key == pygame.K_t:
                    show_trails = not show_trails
                    print(f"[input] trails -> {show_trails}")

                if event.key == pygame.K_r:
                    particles = create_particle_system_from_image(cfg)
                    print("[input] particles regenerated from image")

        # Обновление частиц
        for p in particles:
            p.update(mouse_pos, cfg, attraction_strength, jitter_amount)

        # Рендер
        if show_trails:
            # Накладываем полупрозрачный черный прямоугольник на trail_surface,
            # чтобы старые следы постепенно исчезали.
            # Прозрачность управления: trail_alpha (меньше = следы дольше)
            fade = pygame.Surface((cfg["window_width"], cfg["window_height"]), pygame.SRCALPHA)
            fade.fill((0, 0, 0, trail_alpha))
            # Накладываем на trail_surface — это даёт эффект затухающих следов
            trail_surface.blit(fade, (0, 0))
# Затем рисуем particles на trail_surface (они оставляют след)
            for p in particles:
                pygame.draw.circle(trail_surface, p.color, (int(p.x), int(p.y)), p.size)
            # И отображаем trail_surface поверх экрана
            screen.blit(trail_surface, (0, 0))
        else:
            # если следов нет — чистим экран (обычный режим)
            screen.fill(cfg["background_color"])

        # В режиме без следов нам нужно отрисовать частицы на чистом экране
        if not show_trails:
            for p in particles:
                p.draw(screen)

        # Если следы включены, частицы уже отрисованы на trail_surface и показаны на экране
        if show_trails:
            for p in particles:
                p.draw(screen)

        # ХУД
        try:
            font = pygame.font.SysFont("Arial", 16)
            status = f"Particles: {len(particles)}  | Gravity x{attraction_strength:.1f}  | Trails: {'On' if show_trails else 'Off'}"
            text_surf = font.render(status, True, (200, 200, 200))
            screen.blit(text_surf, (8, 8))
        except Exception:
            # Если шрифты не инициализированы — пропускаем ХУД
            pass

        pygame.display.flip()
        clock.tick(cfg.get("animation_speed", 60))

    pygame.quit()
if __name__ == "__main__":
    main()