import json
import os
import pygame

pygame.init()

WIDTH, HEIGHT = 800, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PytFormer Editor")

clock = pygame.time.Clock()
FPS = 60
font = pygame.font.SysFont(None, 28)

WORLD_Y_OFFSET = 200
CAMERA_SPEED = 8

ENEMY_SIZE = 26
ENEMY_COLOR = (190, 40, 50)
DEFAULT_ENEMY_SPEED = 1.5

SAVE_DIR = "Levels/custom"
os.makedirs(SAVE_DIR, exist_ok=True)

PLAYER_START_COLOR = (60, 160, 90)
PLAYER_START_SIZE = 28

LEVEL_PATHS = {
    pygame.K_1: "Levels/level1.json",
    pygame.K_2: "Levels/level2.json",
    pygame.K_3: "Levels/level3.json",
}

BRUSH_KEYS = {
    pygame.K_q: 0,
    pygame.K_w: 1,
    pygame.K_e: 2,
    pygame.K_r: 3,
}

BRUSH_NAMES = {
    0: "Empty (q)",
    1: "Platform (w)",
    2: "Goal (E)",
    3: "Spike (R)"
}

def switch_level(path):
    global level_data, level_width_px, camera_x, current_level_path
    level_data = load_level(path)
    level_width_px = level_data["tile_size"] * len(level_data["grid"][0])
    camera_x = 0
    current_level_path = path

BG_COLOR = (40, 40, 50)
GRID_LINE_COLOR = (60, 60, 70)
COLORS = {
    1: (100, 65, 30),
    2: (255, 215, 0),
    3: (190, 190, 200),
}

def load_level(path):
    with open(path, "r") as f:
        return json.load(f)

def save_level(path):
    tile_size = level_data["tile_size"]
    ps = level_data["player_start"]

    lines = []
    lines.append("{")
    lines.append(f' "tile_size": {tile_size}, ')
    lines.append(f' "player_start": {{"x": {ps["x"]}, "y": {ps["y"]}}},')
    lines.append('  "grid": [')

    grid_lines = []
    for row in level_data["grid"]:
        grid_lines.append(" [" + ", ".join(str(v) for v in row) + "]")
    lines.append(",\n".join(grid_lines))

    has_enemies = "enemies" in level_data and len(level_data["enemies"]) > 0
    lines.append(" ]," if has_enemies else " ]")

    if has_enemies:
        lines.append(' "enemies": [')
        enemy_lines = []
        for e in level_data["enemies"]:
            enemy_lines.append(
                f' {{"x": {e["x"]}, "y": {e["y"]}, '
                f'"patrol_range": {e["patrol_range"]}, "speed": {e["speed"]}}}'
            )
        lines.append(",\n".join(enemy_lines))
        lines.append(" ]")
    lines.append("}")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    print(f"Guardado: {path}")

def draw_grid(surface, level_data, camera_x):
    tile_size = level_data["tile_size"]
    grid = level_data["grid"]

    for row_index, row in enumerate(grid):
        for col_index, value in enumerate(row):
            x = col_index * tile_size - camera_x
            y = row_index * tile_size + WORLD_Y_OFFSET

            if value in COLORS:
                rect = pygame.Rect(x, y, tile_size, tile_size)
                pygame.draw.rect(surface, COLORS[value], rect)

            empty_rect = pygame.Rect(x, y, tile_size, tile_size)
            pygame.draw.rect(surface, GRID_LINE_COLOR, empty_rect, width=1)

def draw_player_start(surface, level_data, camera_x):
    ps = level_data["player_start"]
    screen_x = ps["x"] - camera_x
    screen_y = ps["y"] + WORLD_Y_OFFSET
    rect = pygame.Rect(screen_x, screen_y, PLAYER_START_SIZE, PLAYER_START_SIZE)
    pygame.draw.rect(surface, PLAYER_START_COLOR, rect, width=3)

def draw_enemies(surface, level_data, camera_x):
    for e in level_data.get("enemies", []):
        screen_x = e["x"] - camera_x
        screen_y = e["y"] + WORLD_Y_OFFSET
        rect = pygame.Rect(screen_x, screen_y, ENEMY_SIZE, ENEMY_SIZE)
        pygame.draw.rect(surface, ENEMY_COLOR, rect)

        line_y = screen_y + ENEMY_SIZE // 2
        left_x = screen_x + ENEMY_SIZE // 2 - e["patrol_range"]
        right_x = screen_x + ENEMY_SIZE // 2 + e["patrol_range"]
        pygame.draw.line(surface, ENEMY_COLOR, (left_x, line_y), (right_x, line_y), 1)

def find_enemy_at(world_pos, level_data):
    for i, e in enumerate(level_data.get("enemies", [])):
        rect = pygame.Rect(e["x"], e["y"], ENEMY_SIZE, ENEMY_SIZE)
        if rect.collidepoint(world_pos):
            return i
    return None

def find_platform_below(world_x, world_y, level_data):
    tile_size = level_data["tile_size"]
    grid = level_data["grid"]

    col = int(world_x // tile_size)
    start_row = max(0, int(world_y // tile_size))

    if col < 0 or col >= len(grid[0]):
        return None

    for row in range(start_row, len(grid)):
        if grid[row][col] == 1:
            return row * tile_size

    return None

def draw_hud(surface, brush_value, mode, hovered_speed, input_active, input_text):
    if input_active:
        prompt = f"Guardar como: {input_text}_"
        hint = "(Enter para confirmar, Esc para cancelar)"
        label = font.render(prompt, True, (255, 255, 255))
        hint_label = font.render(hint, True, (180, 180, 180))
        surface.blit(label, (10, 10))
        surface.blit(hint_label, (10, 34))
        return
    brush_text = f"Brush: {BRUSH_NAMES[brush_value]}"
    label = font.render(brush_text, True, (255, 255, 255))
    surface.blit(label, (10, 10))

    mode_text = f"Mode: {mode.upper()} (TAB para cambiar)"
    mode_label = font.render(mode_text, True, (255, 255, 255))
    surface.blit(mode_label, (10, 34))

    if hovered_speed is not None:
        speed_text = f"Enemy speed: {hovered_speed} (scroll para ajustar)"
        speed_label = font.render(speed_text, True, (255, 255, 255))
        surface.blit(speed_label, (10, 58))

def screen_to_cell(mouse_pos, level_data, camera_x):
    tile_size = level_data["tile_size"]
    grid = level_data["grid"]

    col = (mouse_pos[0] + camera_x) // tile_size
    row = (mouse_pos[1] - WORLD_Y_OFFSET) // tile_size

    if row < 0 or row >= len(grid):
        return None
    if col < 0 or col >= len(grid[0]):
        return None

    return row, col

def screen_to_world(mouse_pos, camera_x):
    world_x = mouse_pos[0] + camera_x
    world_y = mouse_pos[1] - WORLD_Y_OFFSET
    return world_x, world_y

def paint_cell(mouse_pos, value):
    cell = screen_to_cell(mouse_pos, level_data, camera_x)
    if cell is None:
        return
    row, col = cell

    if value == 2:
        for r, grid_row in enumerate(level_data["grid"]):
            for c, v in enumerate(grid_row):
                if v == 2:
                    level_data["grid"][r][c] = 0
    level_data["grid"][row][col] = value

switch_level("Levels/level1.json")

current_brush = 1
is_painting = False
is_painting_erase = False

current_mode = "tile"
dragging_enemy = False
drag_start_world = None

input_active = False
input_text = ""

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if input_active:
                if event.key == pygame.K_RETURN:
                    if input_text.strip() != "":
                        filename = input_text.strip()
                        if not filename.endswith(".json"):
                            filename += ".json"
                        save_level(os.path.join(SAVE_DIR, filename))
                    input_active = False
                    input_text = ""
                elif event.key == pygame.K_ESCAPE:
                    input_active = False
                    input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isprintable():
                    input_text += event.unicode
            else:
                if event.key in LEVEL_PATHS:
                    switch_level(LEVEL_PATHS[event.key])
                if event.key in BRUSH_KEYS:
                    current_brush = BRUSH_KEYS[event.key]
                if event.key == pygame.K_s:
                    input_active = True
                if event.key == pygame.K_TAB:
                    current_mode = "entity" if current_mode == "tile" else "tile"

        if not input_active:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if current_mode == "tile":
                    if event.button == 1:
                        is_painting = True
                        paint_cell(event.pos, current_brush)
                    if event.button == 3:
                        is_painting_erase = True
                        paint_cell(event.pos, 0)
                elif current_mode == "entity":
                    if event.button == 1:
                        dragging_enemy = True
                        drag_start_world = screen_to_world(event.pos, camera_x)
                    if event.button == 3:
                        world_pos = screen_to_world(event.pos, camera_x)
                        idx = find_enemy_at(world_pos, level_data)
                        if idx is not None:
                            del level_data["enemies"][idx]

            if event.type == pygame.MOUSEBUTTONUP:
                if current_mode == "tile":
                    if event.button == 1:
                        is_painting = False
                    if event.button == 3:
                        is_painting_erase = False
                elif current_mode == "entity":
                    if event.button == 1 and dragging_enemy:
                        end_world = screen_to_world(event.pos, camera_x)
                        patrol_range = abs(end_world[0] - drag_start_world[0])

                        snapped_y = find_platform_below(
                            drag_start_world[0], drag_start_world[1], level_data
                        )
                        if snapped_y is None:
                            dragging_enemy = False
                            continue

                        new_enemy = {
                            "x": drag_start_world[0],
                            "y": snapped_y - ENEMY_SIZE,
                            "patrol_range": patrol_range,
                            "speed": DEFAULT_ENEMY_SPEED
                        }
                        level_data.setdefault("enemies", []).append(new_enemy)
                        dragging_enemy = False
            if event.type == pygame.MOUSEMOTION:
                if current_mode == "tile":
                    if is_painting:
                        paint_cell(event.pos, current_brush)
                    if is_painting_erase:
                        paint_cell(event.pos, 0)
            if event.type == pygame.MOUSEWHEEL:
                if current_mode == "entity":
                    world_pos = screen_to_world(pygame.mouse.get_pos(), camera_x)
                    idx = find_enemy_at(world_pos, level_data)
                    if idx is not None:
                        level_data["enemies"][idx]["speed"] += event.y * 0.1
                        level_data["enemies"][idx]["speed"] = round(
                            max(0.1, level_data["enemies"][idx]["speed"]), 2
                        )
    if not input_active:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            camera_x -= CAMERA_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            camera_x += CAMERA_SPEED
        camera_x = max(0, min(camera_x, level_width_px - WIDTH))

    hovered_speed = None
    if current_mode == "entity" and not input_active:
        world_pos = screen_to_world(pygame.mouse.get_pos(), camera_x)
        idx = find_enemy_at(world_pos, level_data)
        if idx is not None:
            hovered_speed = level_data["enemies"][idx]["speed"]

    screen.fill(BG_COLOR)
    draw_grid(screen, level_data, camera_x)
    draw_player_start(screen, level_data, camera_x)
    draw_enemies(screen, level_data, camera_x)
    draw_hud(screen, current_brush, current_mode, hovered_speed, input_active, input_text)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()