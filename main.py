import json
import math
import pygame

pygame.init()

WIDTH, HEIGHT = 800, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PytFormer")

clock = pygame.time.Clock()
FPS = 60

GRAVITY = 0.9                                                                  # CAMBIO (era 0.8)
JUMP_STRENGTH = -12                                                            # CAMBIO (era -15)
PLAYER_SPEED = 4                                                               # CAMBIO (era 5)
COYOTE_FRAMES = 6

LEVEL_PATHS = [
    "Levels/level1.json",
    "Levels/level2.json",
    "Levels/level3.json",
]

# --- Colores ---
SKY_TOP = (110, 180, 230)
SKY_BOTTOM = (200, 235, 250)
MOUNTAIN_COLOR = (130, 155, 180)
DIRT_COLOR = (100, 65, 30)
DIRT_OUTLINE = (60, 40, 20)
GRASS_COLOR = (90, 170, 70)
GOAL_COLOR = (255, 215, 0)
GOAL_OUTLINE = (200, 160, 0)
SPIKE_COLOR = (190, 190, 200)
SPIKE_OUTLINE = (90, 90, 100)
ENEMY_COLOR = (190, 40, 50)
ENEMY_OUTLINE = (110, 20, 25)

MOUNTAIN_WIDTH = 220
MOUNTAIN_HEIGHT = 140
WORLD_Y_OFFSET = 200


def load_level(path):
    with open(path, "r") as f:
        return json.load(f)


def get_tiles_by_value(level_data, value):
    tile_size = level_data["tile_size"]
    grid = level_data["grid"]
    result = []
    for row_index, row in enumerate(grid):
        for col_index, v in enumerate(row):
            if v == value:
                x = col_index * tile_size
                y = row_index * tile_size + WORLD_Y_OFFSET
                result.append(pygame.Rect(x, y, tile_size, tile_size))
    return result

def build_enemies(level_data):
    entries = level_data.get("enemies", [])
    enemies = []
    for e in entries:
        rect = pygame.Rect(e["x"], e["y"] + WORLD_Y_OFFSET, 26, 26)
        enemies.append({
            "rect": rect,
            "start_x": e["x"],
            "patrol_range": e.get("patrol_range", 100),
            "speed": e.get("speed", 1,5),
            "direction": 1,
        })
    return enemies

def update_enemies(enemies):
    for enemy in enemies:
        enemy["rect"].x += enemy["speed"] * enemy["direction"]
        if enemy["rect"].x > enemy["start_x"] + enemy["patrol_range"]:
            enemy["directiom"] = -1
        elif enemy["rect"].x > enemy["star_x"] - enemy["patrol_range"]:
            enemy["direction"] = 1


def move_and_collide(player, velocity_x, velocity_y, tiles):
    on_ground = False

    player.x += velocity_x
    for tile in tiles:
        if player.colliderect(tile):
            if velocity_x > 0:
                player.right = tile.left
            elif velocity_x < 0:
                player.left = tile.right

    player.y += velocity_y
    for tile in tiles:
        if player.colliderect(tile):
            if velocity_y > 0:
                player.bottom = tile.top
                on_ground = True
                velocity_y = 0
            elif velocity_y < 0:
                player.top = tile.bottom
                velocity_y = 0

    return velocity_y, on_ground

def respawn_player(state):
    state["player"].x, state["player"].y = state["player_start"]
    state["velocity_y"] = 0

def draw_background(surface, camera_x):
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
        g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
        b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

    parallax_factor = 0.3
    offset = int(camera_x * parallax_factor) % MOUNTAIN_WIDTH
    x = -offset - MOUNTAIN_WIDTH
    while x < WIDTH + MOUNTAIN_WIDTH:
        points = [
            (x, HEIGHT),
            (x + MOUNTAIN_WIDTH // 2, HEIGHT - MOUNTAIN_HEIGHT),
            (x + MOUNTAIN_WIDTH, HEIGHT),
        ]
        pygame.draw.polygon(surface, MOUNTAIN_COLOR, points)
        x += MOUNTAIN_WIDTH


def draw_tile(surface, tile, camera_x):
    draw_rect = tile.move(-camera_x, 0)
    pygame.draw.rect(surface, DIRT_COLOR, draw_rect)
    grass_rect = pygame.Rect(draw_rect.x, draw_rect.y, draw_rect.width, 6)     # CAMBIO (era 8, un poco mas fino para tiles chicos)
    pygame.draw.rect(surface, GRASS_COLOR, grass_rect)
    pygame.draw.rect(surface, DIRT_OUTLINE, draw_rect, width=2)


def draw_goal(surface, goal, camera_x):
    draw_rect = goal.move(-camera_x, 0)
    pygame.draw.rect(surface, GOAL_COLOR, draw_rect, border_radius=4)          # CAMBIO (era 6)
    pygame.draw.rect(surface, GOAL_OUTLINE, draw_rect, width=2, border_radius=4)  # CAMBIO (era width=3, border_radius=6)

def draw_spike(surface, tile, camera_x):
    draw_rect = tile.move(-camera_x, 0)
    base_rect = pygame.Rect(draw_rect.x, draw_rect.bottom - 5, draw_rect.witdh, 5)
    pygame.draw.rect(surface, SPIKE_OUTLINE, base_rect)

    spike_count = 3
    spike_w = draw_rect.widht / spike_count
    for i in range(spike_count):
        x0 = draw_rect.x + i * spike_w
        points = [
            (x0, draw_rect.bottom - 5),
            (x0, spike_w / 2, draw_rect.top),
            (x0, spike_w, draw_rect.bottom - 5),
        ]
        pygame.draw.polygon(surface, SPIKE_COLOR, points)

def draw_enemy(surface, rect, camera_x):
    draw_rect = rect.move(-camera_x, 0)
    pygame.draw.ellipse(surface, ENEMY_COLOR, draw_rect)
    pygame.draw.ellipse(surface, ENEMY_OUTLINEm, draw_rect, width=2)

    eye_y = draw_rect.centery - 4
    for ex in (draw_rect.centerx - 6, draw_rect.centerx + 6):
        pygame.draw.line(surface, (255, 255, 255), (ex - 3, eye_y - 3), (ex + 3, eye_y + 3), 2)
        pygame.draw.line(surface, (255, 255, 255), (ex - 3, eye_y + 3), (ex + 3, eye_y - 3), 2)

def draw_player(surface, rect, facing_right, walk_frame, squash_y):
    body_color = (60, 160, 90)
    outline_color = (30, 90, 50)
    leg_color = (40, 110, 65)

    shadow_width = int(rect.width * 0.8)
    shadow_surface = pygame.Surface((shadow_width, 8), pygame.SRCALPHA)        # CAMBIO (era 10 de alto)
    pygame.draw.ellipse(shadow_surface, (0, 0, 0, 90), shadow_surface.get_rect())
    shadow_pos = (rect.centerx - shadow_width // 2, rect.bottom - 3)          # CAMBIO (era -4)
    surface.blit(shadow_surface, shadow_pos)

    body_rect = pygame.Rect(0, 0, rect.width, int(rect.height * squash_y))
    body_rect.midbottom = rect.midbottom

    leg_swing = math.sin(walk_frame) * 4                                      # CAMBIO (era 6)
    left_leg = pygame.Rect(0, 0, 6, 7)                                       # CAMBIO (era 8, 10)
    left_leg.midtop = (body_rect.centerx - 6, body_rect.bottom - 2 + leg_swing)   # CAMBIO (era -8)
    right_leg = pygame.Rect(0, 0, 6, 7)                                      # CAMBIO (era 8, 10)
    right_leg.midtop = (body_rect.centerx + 6, body_rect.bottom - 2 - leg_swing)  # CAMBIO (era +8)
    pygame.draw.rect(surface, leg_color, left_leg, border_radius=2)           # CAMBIO (era 3)
    pygame.draw.rect(surface, leg_color, right_leg, border_radius=2)          # CAMBIO (era 3)

    pygame.draw.rect(surface, body_color, body_rect, border_radius=7)          # CAMBIO (era 10)
    pygame.draw.rect(surface, outline_color, body_rect, width=2, border_radius=7)  # CAMBIO (era width=3, border_radius=10)

    eye_y = body_rect.top + body_rect.height // 3
    eye_spacing = 7                                                           # CAMBIO (era 10)
    left_eye_x = body_rect.centerx - eye_spacing
    right_eye_x = body_rect.centerx + eye_spacing
    pupil_offset = 1 if facing_right else -1                                  # CAMBIO (era 2/-2)

    for eye_x in (left_eye_x, right_eye_x):
        pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), 4)       # CAMBIO (era 6)
        pygame.draw.circle(surface, (20, 20, 20), (eye_x + pupil_offset, eye_y), 2)  # CAMBIO (era 3)


def start_level(index):
    level_data = load_level(LEVEL_PATHS[index])
    tiles = get_tiles_by_value(level_data, 1)
    goal_tiles = get_tiles_by_value(level_data, 2)
    hazard_tiles = get_tiles_by_value(level_data, 3)
    enemies = build_enemies(level_data)

    tile_size = level_data["tile_size"]
    level_width_px = tile_size * len(level_data["grid"][0])

    start = level_data["player_start"]
    player = pygame.Rect(start["x"], start["y"] + WORLD_Y_OFFSET, 28, 42)                      # CAMBIO (era 40, 60)

    return {
        "tiles": tiles,
        "goal_tiles": goal_tiles,
        "hazard_tiles": hazard_tiles,
        "enemies": enemies,
        "level_width_px": level_width_px,
        "player": player,
        "player_start": (start["x"], start["y"] + WORLD_Y_OFFSET),
        "velocity_y": 0,
        "on_ground": False,
        "coyote_counter": 0,
        "camera_x": 0,
        "facing_right": True,
        "walk_frame": 0.0,
        "squash_y": 1.0,
    }


current_level_index = 0
state = start_level(current_level_index)
game_won = False

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and state["coyote_counter"] > 0:
                state["velocity_y"] = JUMP_STRENGTH
                state["coyote_counter"] = 0
                state["squash_y"] = 1.25

    if not game_won:
        keys = pygame.key.get_pressed()
        velocity_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            velocity_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            velocity_x = PLAYER_SPEED

        if velocity_x > 0:
            state["facing_right"] = True
        elif velocity_x < 0:
            state["facing_right"] = False

        was_on_ground = state["on_ground"]

        state["velocity_y"] += GRAVITY
        state["velocity_y"], state["on_ground"] = move_and_collide(
            state["player"], velocity_x, state["velocity_y"], state["tiles"]
        )

        if state["on_ground"] and not was_on_ground:
            state["squash_y"] = 0.65

        state["squash_y"] += (1.0 - state["squash_y"]) * 0.25

        if velocity_x != 0 and state["on_ground"]:
            state["walk_frame"] += 0.3
        else:
            state["walk_frame"] = 0.0

        if state["on_ground"]:
            state["coyote_counter"] = COYOTE_FRAMES
        else:
            state["coyote_counter"] = max(0, state["coyote_counter"] - 1)
        
        update_enemies(state["enemies"])

        if state["player"].top > HEIGHT + 200:
            respawn_player(state)
        
        for hazard in state["hazard_tiles"]:
            if state["player"].collideract(hazard):
                respawn_player(state)
                break
        
        for enemy in state["enemies"]:
            if state["player"].colliderect(enemy["rect"]):
                respawn_player(state)
                break

        for goal in state["goal_tiles"]:
            if state["player"].colliderect(goal):
                current_level_index += 1
                if current_level_index >= len(LEVEL_PATHS):
                    game_won = True
                else:
                    state = start_level(current_level_index)
                break

        state["camera_x"] = state["player"].centerx - WIDTH // 2
        state["camera_x"] = max(0, min(state["camera_x"], state["level_width_px"] - WIDTH))

    draw_background(screen, state["camera_x"])

    if not game_won:
        camera_x = state["camera_x"]

        for tile in state["tiles"]:
            draw_tile(screen, tile, camera_x)
        
        for hazard in state["hazard_tiles"]:
            draw_spike(screen, hazard, camera_x)

        for goal in state["goal_tiles"]:
            draw_goal(screen, goal, camera_x)
        
        for enemy in state["enemies"]:
            draw_enemy(screen, enemy["rect"], camera_x)

        draw_player(
            screen,
            state["player"].move(-camera_x, 0),
            state["facing_right"],
            state["walk_frame"],
            state["squash_y"],
        )
    else:
        font = pygame.font.SysFont(None, 64)
        text = font.render("YOU WIN!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()