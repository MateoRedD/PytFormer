import pygame
import json

pygame.init()

WIDTH, HEIGHT = 800, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PytFormer")

clock = pygame.time.Clock()
FPS = 60

COYOTE_FRAMES = 6
coyote_counter = 0
GRAVITY = 0.8
JUMP_STRENGHT = -15
PLAYER_SPEED = 5

LEVEL_PATHS = [
    "Levels/level1.json",
    "Levels/level2.json",
    "Levels/level2.json",
]

def load_level(path):
    with open(path, "r") as f:
        return json.load(f)

def get_tiles_by_value(level_data, value):
    """Devuelve una lista de Rects para cada celda de la grilla que tenga este valor."""
    tile_size = level_data["tile_size"]
    grid = level_data["grid"]
    result = []
    for row_index, row in enumerate(grid):
        for col_index, v in enumerate(row):
            if v == value:
                x = col_index * tile_size
                y = row_index * tile_size
                result.append(pygame.Rect(x, y, tile_size, tile_size))
    return result

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

def start_level(index):
    """Carga el nivel en LEVEL_PATHS[index] y arma el estado inicial completo.""" 
    level_data = load_level(LEVEL_PATHS[index])
    tiles = get_tiles_by_value(level_data, 1)
    goal_tiles = get_tiles_by_value(level_data, 2)

    tile_size = level_data["tile_size"]
    level_width_px = tile_size * len(level_data["grid"][0])

    start = level_data["player_start"]
    player = pygame.Rect(start["x"], start["y"], 40, 60)

    return{
        "tiles": tiles,
        "goal_tiles": goal_tiles,
        "level_width_px": level_width_px,
        "player": player,
        "velocity_y": 0,
        "on_ground": False,
        "coyote_counter": 0,
        "camera_x": 0,
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
                state["velocity_y"] = JUMP_STRENGHT
                state["coyote_counter"] = 0
            
    if not game_won:
        keys = pygame.key.get_pressed()
        velocity_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            velocity_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            velocity_x = PLAYER_SPEED
        
        state["velocity_y"] += GRAVITY
        state["velocity_y"], state["on_ground"] = move_and_collide(
            state["player"], velocity_x, state["velocity_y"], state["tiles"]
        )
        if state["on_ground"]:
            state["coyote_counter"] = COYOTE_FRAMES
        else:
            state["coyote_counter"] = max(0, state["coyote_counter"] - 1)
        
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
    
    screen.fill((135, 206, 235))

    if not game_won:
        camera_x = state["camera_x"]

        for tile in state["tiles"]:
            pygame.draw.rect(screen, (80, 50, 20), tile.move(-camera_x, 0))
        
        for goal in state["goal_tiles"]:
            pygame.draw.rect(screen, (255, 215, 0), goal.move(-camera_x, 0))
        
        pygame.draw.rect(screen, (200, 50, 50), state["player"].move(-camera_x, 0))
        
    else:
        Font = pygame.font.SysFont(None, 64)
        text = Font.render("YOU WIN!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text, text_rect)
    
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()


            
   