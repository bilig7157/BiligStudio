import pygame
import math
import random
import os
import sys
import time

pygame.init()
pygame.mouse.set_visible(False)
WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("世界大战 3D 迷宫 - Bilig Studio")
clock = pygame.time.Clock()

# ===== 字体 =====
def get_cn_font(size, bold=False):
    if bold:
        path = r"C:\Windows\Fonts\msyhbd.ttc"
    else:
        path = r"C:\Windows\Fonts\msyh.ttc"
    if os.path.exists(path):
        return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)

font_big = get_cn_font(72, bold=True)
font_mid = get_cn_font(36)
font_small = get_cn_font(24)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
RED = (220, 60, 60)
GREEN = (80, 200, 80)

TILE_SIZE = 40
FOV = math.pi / 3
RAY_COUNT = 120
MAX_DEPTH = 300

LEVELS = [
    {"name": "第一关：新手训练", "map_base": 7,  "bot_count": 2, "bot_hp": 30,  "bot_speed": 0.8},
    {"name": "第二关：迷宫深处", "map_base": 9,  "bot_count": 3, "bot_hp": 50,  "bot_speed": 1.0},
    {"name": "第三关：死亡走廊", "map_base": 11, "bot_count": 5, "bot_hp": 70,  "bot_speed": 1.2},
    {"name": "第四关：血色迷宫", "map_base": 13, "bot_count": 6, "bot_hp": 100, "bot_speed": 1.4},
    {"name": "第五关：终极试炼", "map_base": 15, "bot_count": 8, "bot_hp": 150, "bot_speed": 1.6},
]

player_x = 1.5 * TILE_SIZE
player_y = 1.5 * TILE_SIZE
player_angle = 0
player_hp = 100
player_ammo = 30
player_score = 0
move_speed = 1.8

RELOAD_AMOUNT = 100

robots = []
ROBOT_SHOOT_RANGE = 200
ROBOT_SHOOT_COOLDOWN = 1.5
robot_bullets = []
BULLET_SPEED = 6

game_state = "splash"
level_index = 0
level_cleared = False
exit_x, exit_y = 0, 0
map_w, map_h = 0, 0
game_map = []

def generate_maze(w, h):
    maze = [[1 for _ in range(w)] for _ in range(h)]
    def carve(cx, cy):
        maze[cy][cx] = 0
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 1 <= nx < w - 1 and 1 <= ny < h - 1 and maze[ny][nx] == 1:
                maze[cy + dy // 2][cx + dx // 2] = 0
                carve(nx, ny)
    carve(1, 1)
    maze[h - 2][w - 2] = 0
    return maze

def start_level(idx):
    global game_map, map_w, map_h, robots, player_x, player_y
    global player_angle, player_hp, player_ammo, level_cleared
    global exit_x, exit_y, robot_bullets, game_state

    cfg = LEVELS[idx]
    map_w = cfg["map_base"]
    map_h = cfg["map_base"]
    if map_w > 31: map_w = 31
    if map_h > 31: map_h = 31
    if map_w % 2 == 0: map_w += 1
    if map_h % 2 == 0: map_h += 1

    game_map = generate_maze(map_w, map_h)

    player_x = 1.5 * TILE_SIZE
    player_y = 1.5 * TILE_SIZE
    player_angle = 0
    player_hp = 100
    player_ammo = 30 + idx * 10
    robot_bullets.clear()
    level_cleared = False

    exit_x = (map_w - 2) * TILE_SIZE + TILE_SIZE // 2
    exit_y = (map_h - 2) * TILE_SIZE + TILE_SIZE // 2
    game_map[map_h - 2][map_w - 2] = 0
    game_map[map_h - 2][map_w - 3] = 0
    game_map[map_h - 3][map_w - 2] = 0

    robots.clear()
    for _ in range(cfg["bot_count"]):
        while True:
            rx = random.randint(2, map_w - 3)
            ry = random.randint(2, map_h - 3)
            if game_map[ry][rx] == 0:
                robots.append({
                    "x": rx * TILE_SIZE + TILE_SIZE // 2,
                    "y": ry * TILE_SIZE + TILE_SIZE // 2,
                    "hp": cfg["bot_hp"],
                    "max_hp": cfg["bot_hp"],
                    "last_shot": 0,
                    "state": "patrol",
                    "dir": random.uniform(0, 2 * math.pi),
                    "speed": cfg["bot_speed"] + random.uniform(-0.2, 0.2),
                })
                break

    game_state = "playing"

def cast_ray(px, py, angle):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)
    distance = 0
    step = 2
    side = 0
    hit_robot = None
    robot_dist = MAX_DEPTH

    while distance < MAX_DEPTH:
        distance += step
        test_x = int((px + cos_a * distance) / TILE_SIZE)
        test_y = int((py + sin_a * distance) / TILE_SIZE)

        for r in robots:
            rdist = math.hypot(r["x"] - px - cos_a * distance,
                               r["y"] - py - sin_a * distance)
            if rdist < 15 and distance < robot_dist:
                hit_robot = r
                robot_dist = distance

        if test_x < 0 or test_x >= map_w or test_y < 0 or test_y >= map_h:
            distance = MAX_DEPTH
            break
        if game_map[test_y][test_x] == 1:
            break

    return distance, side, hit_robot, robot_dist

def render_3d():
    screen.fill((60, 60, 80), (0, 0, WIDTH, HEIGHT // 2))
    screen.fill((40, 40, 40), (0, HEIGHT // 2, WIDTH, HEIGHT // 2))

    ray_angle = player_angle - FOV / 2
    ray_step = FOV / RAY_COUNT
    strip_w = WIDTH / RAY_COUNT

    for i in range(RAY_COUNT):
        dist, side, hit_robot, robot_dist = cast_ray(player_x, player_y, ray_angle)
        corr_dist = dist * math.cos(player_angle - ray_angle)
        if corr_dist <= 0: corr_dist = 0.01

        wall_h = min(int(HEIGHT / corr_dist * TILE_SIZE / 2), HEIGHT)
        shade = max(50, 255 - int(corr_dist * 0.8))
        if side == 1:
            shade = int(shade * 0.7)

        strip_x = int(i * strip_w)
        strip_y = HEIGHT // 2 - wall_h // 2
        pygame.draw.rect(screen, (shade, shade, shade), (strip_x, strip_y, int(strip_w) + 1, wall_h))

        if hit_robot and robot_dist < corr_dist:
            r_corr = robot_dist * math.cos(player_angle - ray_angle)
            if r_corr > 0:
                bot_h = min(int(HEIGHT / r_corr * TILE_SIZE), HEIGHT)
                bot_y = HEIGHT // 2 - bot_h // 2
                hp_ratio = hit_robot["hp"] / hit_robot["max_hp"]
                bot_color = (int(200 * hp_ratio + 55), 30, 30)
                pygame.draw.rect(screen, bot_color, (strip_x, bot_y, int(strip_w) + 1, bot_h))

                bar_w = max(int(strip_w * 3), 20)
                bar_h = 4
                bar_x = strip_x + int(strip_w) // 2 - bar_w // 2
                bar_y = bot_y - 10
                pygame.draw.rect(screen, (80, 0, 0), (bar_x, bar_y, bar_w, bar_h))
                fill_w = int(bar_w * hp_ratio)
                if fill_w > 0:
                    pygame.draw.rect(screen, GREEN, (bar_x, bar_y, fill_w, bar_h))

        ray_angle += ray_step

def draw_minimap():
    mm_size = 5
    mm_x = WIDTH - map_w * mm_size - 10
    mm_y = 10
    for y in range(map_h):
        for x in range(map_w):
            color = (60, 60, 60) if game_map[y][x] == 1 else (20, 20, 20)
            pygame.draw.rect(screen, color, (mm_x + x * mm_size, mm_y + y * mm_size, mm_size, mm_size))

    pygame.draw.rect(screen, GREEN,
        (mm_x + int(exit_x // TILE_SIZE) * mm_size,
         mm_y + int(exit_y // TILE_SIZE) * mm_size, mm_size, mm_size))

    for r in robots:
        rx = mm_x + int(r["x"] // TILE_SIZE) * mm_size
        ry = mm_y + int(r["y"] // TILE_SIZE) * mm_size
        pygame.draw.circle(screen, RED, (rx + mm_size // 2, ry + mm_size // 2), 2)

    px = mm_x + int(player_x // TILE_SIZE) * mm_size
    py = mm_y + int(player_y // TILE_SIZE) * mm_size
    pygame.draw.circle(screen, YELLOW, (px + mm_size // 2, py + mm_size // 2), 3)

def collide(x, y):
    tx = int(x / TILE_SIZE)
    ty = int(y / TILE_SIZE)
    if tx < 0 or tx >= map_w or ty < 0 or ty >= map_h:
        return True
    return game_map[ty][tx] == 1

def move_entity(ex, ey, nx, ny):
    if not collide(nx, ey):
        ex = nx
    if not collide(ex, ny):
        ey = ny
    return ex, ey

def splash_screen():
    start = time.time()
    while time.time() - start < 3.0:
        for event in pygame.event.get():
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((15, 15, 20))
        cx, cy = WIDTH // 2, HEIGHT // 2
        title = font_big.render("Bilig Studio", True, YELLOW)
        screen.blit(title, (cx - title.get_width() // 2, cy - 40))
        sub = font_small.render("v3.0  ·  3D Maze", True, (120, 120, 120))
        screen.blit(sub, (cx - sub.get_width() // 2, cy + 30))
        tip = font_small.render("按任意键跳过", True, (80, 80, 80))
        screen.blit(tip, (cx - tip.get_width() // 2, cy + 80))
        pygame.display.flip()
        clock.tick(60)

splash_screen()
game_state = "menu"

running = True
while running:
    dt = clock.tick(60) / 1000.0
    now = time.time()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state = "menu"

            # F 键：直接 +100 发
            if event.key == pygame.K_f:
                player_ammo += RELOAD_AMOUNT

            if game_state == "menu" and event.key == pygame.K_RETURN:
                level_index = 0
                player_score = 0
                start_level(level_index)

            if game_state == "cleared" and event.key == pygame.K_RETURN:
                level_index += 1
                if level_index >= len(LEVELS):
                    game_state = "victory"
                else:
                    start_level(level_index)

            if game_state == "gameover" and event.key == pygame.K_RETURN:
                start_level(level_index)

            if game_state == "victory" and event.key == pygame.K_RETURN:
                game_state = "menu"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "playing" and player_ammo > 0:
                player_ammo -= 1
                for r in robots[:]:
                    dx = r["x"] - player_x
                    dy = r["y"] - player_y
                    dist = math.hypot(dx, dy)
                    angle_to = math.atan2(dy, dx)
                    angle_diff = abs(((angle_to - player_angle + math.pi) % (2 * math.pi)) - math.pi)
                    if dist < 300 and angle_diff < 0.15:
                        r["hp"] -= 25
                        if r["hp"] <= 0:
                            robots.remove(r)
                            player_score += 100
                        break
                else:
                    player_score += 10

    if pygame.mouse.get_focused() and game_state == "playing":
        rel_x, _ = pygame.mouse.get_rel()
        player_angle += rel_x * 0.002
        player_angle %= 2 * math.pi
        pygame.mouse.set_pos(WIDTH // 2, HEIGHT // 2)

    keys = pygame.key.get_pressed()

    if game_state == "playing":
        move_dx = 0
        move_dy = 0
        if keys[pygame.K_w]:
            move_dx += math.cos(player_angle) * move_speed
            move_dy += math.sin(player_angle) * move_speed
        if keys[pygame.K_s]:
            move_dx -= math.cos(player_angle) * move_speed
            move_dy -= math.sin(player_angle) * move_speed
        if keys[pygame.K_a]:
            move_dx += math.cos(player_angle - math.pi / 2) * move_speed * 0.7
            move_dy += math.sin(player_angle - math.pi / 2) * move_speed * 0.7
        if keys[pygame.K_d]:
            move_dx += math.cos(player_angle + math.pi / 2) * move_speed * 0.7
            move_dy += math.sin(player_angle + math.pi / 2) * move_speed * 0.7

        player_x, player_y = move_entity(player_x, player_y,
                                          player_x + move_dx, player_y + move_dy)

        if not level_cleared and math.hypot(player_x - exit_x, player_y - exit_y) < TILE_SIZE:
            level_cleared = True
            player_score += 500
            game_state = "cleared"

        for r in robots[:]:
            dx = player_x - r["x"]
            dy = player_y - r["y"]
            dist = math.hypot(dx, dy)
            angle_to = math.atan2(dy, dx)

            can_see = False
            if dist < 250:
                dangle = abs(((angle_to - r["dir"] + math.pi) % (2 * math.pi)) - math.pi)
                if dangle < 0.6:
                    steps = int(dist / 10)
                    clear = True
                    for s in range(1, steps):
                        tx = r["x"] + dx * s / steps
                        ty = r["y"] + dy * s / steps
                        if collide(tx, ty):
                            clear = False
                            break
                    if clear:
                        can_see = True

            if can_see:
                r["state"] = "chase"
                r["dir"] = angle_to
                if dist > 60:
                    nx = r["x"] + math.cos(r["dir"]) * r["speed"]
                    ny = r["y"] + math.sin(r["dir"]) * r["speed"]
                    r["x"], r["y"] = move_entity(r["x"], r["y"], nx, ny)
                if now - r["last_shot"] > ROBOT_SHOOT_COOLDOWN and dist < ROBOT_SHOOT_RANGE:
                    robot_bullets.append({
                        "x": r["x"], "y": r["y"],
                        "dx": math.cos(angle_to) * BULLET_SPEED,
                        "dy": math.sin(angle_to) * BULLET_SPEED
                    })
                    r["last_shot"] = now
            else:
                r["state"] = "patrol"
                if random.random() < 0.02:
                    r["dir"] += random.uniform(-0.5, 0.5)
                nx = r["x"] + math.cos(r["dir"]) * r["speed"] * 0.5
                ny = r["y"] + math.sin(r["dir"]) * r["speed"] * 0.5
                if collide(nx, ny):
                    r["dir"] = random.uniform(0, 2 * math.pi)
                else:
                    r["x"], r["y"] = nx, ny

        for b in robot_bullets[:]:
            b["x"] += b["dx"]
            b["y"] += b["dy"]
            if collide(b["x"], b["y"]):
                robot_bullets.remove(b)
            elif math.hypot(b["x"] - player_x, b["y"] - player_y) < 15:
                player_hp -= 10
                robot_bullets.remove(b)
                if player_hp <= 0:
                    game_state = "gameover"

    screen.fill(BLACK)

    if game_state == "menu":
        screen.fill((15, 15, 20))
        title = font_big.render("世界大战 3D 迷宫", True, YELLOW)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))
        sub = font_mid.render("Bilig Studio", True, WHITE)
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 190))
        tip = font_mid.render("按 Enter 开始游戏", True, GREEN)
        screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, 300))
        tip2 = font_small.render("WASD 移动 | 鼠标转向 | 左键射击 | F 加弹 | ESC 菜单", True, (150, 150, 150))
        screen.blit(tip2, (WIDTH // 2 - tip2.get_width() // 2, 420))

    elif game_state in ("playing", "cleared", "gameover"):
        render_3d()
        draw_minimap()

        hp_color = GREEN if player_hp > 50 else RED
        pygame.draw.rect(screen, (50, 0, 0), (10, 10, 204, 24))
        pygame.draw.rect(screen, hp_color, (12, 12, max(0, player_hp) * 2, 20))
        hp_text = font_small.render(f"HP: {max(0, player_hp)}", True, WHITE)
        screen.blit(hp_text, (20, 14))

        ammo_text = font_small.render(f"弹药: {player_ammo}  (F+100)", True, WHITE)
        screen.blit(ammo_text, (10, 40))

        level_name = LEVELS[level_index]["name"]
        level_text = font_small.render(f"{level_name} ({level_index + 1}/{len(LEVELS)})", True, WHITE)
        screen.blit(level_text, (10, 65))

        score_text = font_small.render(f"Score: {player_score}", True, WHITE)
        screen.blit(score_text, (10, 90))

        pygame.draw.circle(screen, WHITE, (WIDTH // 2, HEIGHT // 2), 3)

        if game_state == "cleared":
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(150)
            overlay.fill((0, 0, 0))
            screen.blit(overlay, (0, 0))
            clear = font_big.render("关卡完成！", True, GREEN)
            screen.blit(clear, (WIDTH // 2 - clear.get_width() // 2, HEIGHT // 2 - 60))
            if level_index + 1 >= len(LEVELS):
                nxt = font_mid.render("最终关卡已通关！按 Enter 查看结局", True, YELLOW)
            else:
                nxt = font_mid.render("按 Enter 进入下一关", True, WHITE)
            screen.blit(nxt, (WIDTH // 2 - nxt.get_width() // 2, HEIGHT // 2 + 10))

        if game_state == "gameover":
            over = font_big.render("GAME OVER", True, RED)
            screen.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 50))
            restart = font_mid.render("按 Enter 重新挑战本关", True, WHITE)
            screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2 + 20))

    elif game_state == "victory":
        screen.fill((10, 10, 30))
        vic = font_big.render("游戏通关！", True, YELLOW)
        screen.blit(vic, (WIDTH // 2 - vic.get_width() // 2, 120))
        score_final = font_mid.render(f"最终得分: {player_score}", True, WHITE)
        screen.blit(score_final, (WIDTH // 2 - score_final.get_width() // 2, 220))
        tip = font_mid.render("按 Enter 返回主菜单", True, GREEN)
        screen.blit(tip, (WIDTH // 2 - tip.get_width() // 2, 320))
        credit = font_small.render("Bilig Studio", True, (100, 100, 100))
        screen.blit(credit, (WIDTH // 2 - credit.get_width() // 2, 450))

    pygame.display.flip()

pygame.quit()