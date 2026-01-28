import pygame
import math
import random

# --- 常數設定 ---
# 視窗配置
GAME_WIDTH = 500  # 遊戲區寬度
UI_WIDTH = 200    # 儀表板寬度
WIDTH, HEIGHT = GAME_WIDTH + UI_WIDTH, 600

CAR_SIZE = (40, 80)
FPS = 60

# 道路設定
LANE_WIDTH = 80
NUM_LANES = 3
ROAD_WIDTH = LANE_WIDTH * NUM_LANES  # 3 * 80 = 240
ROAD_X = (GAME_WIDTH - ROAD_WIDTH) // 2 # 道路置中

# 顏色定義
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
UI_BG_COLOR = (50, 50, 60)

class Car:
    def __init__(self, x, y):
        self.original_image = pygame.Surface(CAR_SIZE, pygame.SRCALPHA)
        pygame.draw.rect(self.original_image, GREEN, (0, 0, CAR_SIZE[0], CAR_SIZE[1]), border_radius=5)
        # 車頭燈 (黃色)
        pygame.draw.rect(self.original_image, YELLOW, (5, 0, 10, 5))
        pygame.draw.rect(self.original_image, YELLOW, (CAR_SIZE[0]-15, 0, 10, 5))
        # 車尾燈 (紅色，倒車時視覺輔助)
        pygame.draw.rect(self.original_image, (150, 0, 0), (5, CAR_SIZE[1]-5, 10, 5))
        pygame.draw.rect(self.original_image, (150, 0, 0), (CAR_SIZE[0]-15, CAR_SIZE[1]-5, 10, 5))
        
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        self.position = pygame.math.Vector2(x, y)
        self.angle = 0 
        self.speed = 0 
        self.max_speed = 15 
        self.min_speed = -5 # 啟用倒車功能
        self.radars = [] 
        self.alive = True
        self.distance_traveled = 0

    def handle_input(self):
        if not self.alive:
            return

        keys = pygame.key.get_pressed()
        
        # 左右平移
        if keys[pygame.K_LEFT]:
            self.position.x -= 6
            self.angle = 5
        elif keys[pygame.K_RIGHT]:
            self.position.x += 6
            self.angle = -5
        else:
            self.angle = 0

        # 油門與倒車控制
        if keys[pygame.K_UP]:
            self.speed = min(self.speed + 0.2, self.max_speed)
        elif keys[pygame.K_DOWN]:
            self.speed = max(self.speed - 0.5, self.min_speed) # 允許倒車到 -5
        else:
            # 自然減速 (摩擦力)
            if self.speed > 0:
                self.speed = max(self.speed - 0.1, 0)
            elif self.speed < 0:
                self.speed = min(self.speed + 0.1, 0)

    def update(self, walls, npcs):
        # 限制移動範圍
        self.position.x = max(ROAD_X + 20, min(self.position.x, ROAD_X + ROAD_WIDTH - 20))
        
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect(center=self.position)
        
        self.check_collision(walls, npcs)
        
        # 360度雷達更新
        self.radars.clear()
        # 定義 8 個方向: 0(前), 45(左前), 90(左), 135(左後), 180(後), -135(右後), -90(右), -45(右前)
        # 為了讓儀表板顯示順序直觀，我們依順時針或逆時針排序
        # 這裡順序: 前 -> 左前 -> 左 -> 左後 -> 後 -> 右後 -> 右 -> 右前
        sensor_angles = [0, 45, 90, 135, 180, -135, -90, -45]
        
        for degree in sensor_angles: 
            self.cast_ray(degree, walls, npcs)
            
        if self.alive:
            self.distance_traveled += self.speed

    def check_collision(self, walls, npcs):
        if not self.alive:
            return

        for wall in walls:
            if self.rect.colliderect(wall):
                self.alive = False
                break
        for npc in npcs:
            if self.rect.colliderect(npc.rect):
                self.alive = False
                break

    def cast_ray(self, angle_offset, walls, npcs):
        length = 0
        max_length = 200 # 雷達長度
        
        rad = math.radians(90 + angle_offset)
        dx = math.cos(rad)
        dy = -math.sin(rad) 
        
        # 修改點 2: 雷達發射點改為「車身中心」，實現真正的 360 度環景
        x, y = self.position.x, self.position.y
        
        while length < max_length:
            x += dx * 3
            y += dy * 3 
            length += 3
            
            point_rect = pygame.Rect(x, y, 4, 4)
            hit = False
            
            # 檢測牆壁
            for wall in walls:
                if wall.colliderect(point_rect):
                    hit = True
                    break
            
            # 檢測 NPC 車輛
            for npc in npcs:
                if npc.rect.colliderect(point_rect):
                    hit = True
                    break

            if hit:
                break
                
        dist = int(math.sqrt((x - self.position.x)**2 + (y - self.position.y)**2))
        self.radars.append(((x, y), dist))

    def draw(self, screen, show_radar=True):
        # 為了不讓雷達線蓋住車子，我們先畫雷達，再畫車子 (或者反過來，看需求)
        # 這裡保持先畫車子，雷達線畫在上面比較清楚看到它射去哪裡
        
        if not self.alive:
            filter_surf = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            filter_surf.fill((255, 0, 0, 100))
            screen.blit(self.image, self.rect)
            screen.blit(filter_surf, self.rect)
        else:
            screen.blit(self.image, self.rect)
        
        if show_radar:
            for radar in self.radars:
                 end_pos, dist = radar
                 color = GREEN
                 if dist < 60: color = RED
                 elif dist < 120: color = YELLOW
                 
                 # 起點是車中心
                 start_pos = (self.position.x, self.position.y)
                 pygame.draw.line(screen, color, start_pos, end_pos, 1)
                 pygame.draw.circle(screen, color, end_pos, 3)

class NPC_Car:
    def __init__(self, lane_index, start_y, speed):
        lane_x = ROAD_X + (lane_index * LANE_WIDTH) + (LANE_WIDTH // 2)
        self.rect = pygame.Rect(0, 0, CAR_SIZE[0], CAR_SIZE[1])
        self.rect.center = (lane_x, start_y) 
        
        self.color = (random.randint(50, 255), random.randint(50, 255), 255)
        self.speed = speed
        self.max_speed = speed 

    def update(self, player_car, npcs):
        closest_dist = 9999
        obstacle_speed = 0
        found_obstacle = False
        
        targets = [player_car] + [npc for npc in npcs if npc != self]

        for target in targets:
            if abs(target.rect.centerx - self.rect.centerx) < 30:
                if target.rect.y < self.rect.y:
                    dist = self.rect.top - target.rect.bottom
                    if dist < closest_dist:
                        closest_dist = dist
                        obstacle_speed = target.speed
                        found_obstacle = True

        if found_obstacle and closest_dist < 400:
            brake_force = 0.2
            if closest_dist < 150: brake_force = 0.8 
            elif closest_dist < 250: brake_force = 0.4 

            target_speed_limit = max(0, obstacle_speed - 1)
            if self.speed > target_speed_limit:
                self.speed -= brake_force
        else:
            if self.speed < self.max_speed:
                self.speed += 0.1

        relative_speed = player_car.speed - self.speed
        self.rect.y += relative_speed

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)

def draw_sidebar(screen, car, show_radar):
    pygame.draw.rect(screen, UI_BG_COLOR, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
    pygame.draw.line(screen, WHITE, (GAME_WIDTH, 0), (GAME_WIDTH, HEIGHT), 2)
    
    font = pygame.font.SysFont('Arial', 20)
    title_font = pygame.font.SysFont('Arial', 24, bold=True)
    
    screen.blit(title_font.render("Dashboard", True, YELLOW), (GAME_WIDTH + 20, 30))
    
    y = 70
    gap = 35
    
    # 速度與距離
    screen.blit(font.render(f"Speed: {car.speed:.1f} km/h", True, WHITE), (GAME_WIDTH + 20, y))
    y += gap
    screen.blit(font.render(f"Dist: {int(car.distance_traveled)} m", True, WHITE), (GAME_WIDTH + 20, y))
    y += gap
    
    # 狀態
    status_text = "ALIVE" if car.alive else "CRASHED"
    status_color = GREEN if car.alive else RED
    screen.blit(title_font.render(status_text, True, status_color), (GAME_WIDTH + 20, y))

    y += gap + 10
    screen.blit(font.render(f"360 Sensors:", True, GRAY), (GAME_WIDTH + 20, y))
    y += 25
    
    # 顯示 8 個方位的數據
    lidar_font = pygame.font.SysFont('Arial', 14)
    text_color = WHITE if show_radar else GRAY
    
    labels = ["Front", "F-Left", "Left", "R-Left", "Rear", "R-Right", "Right", "F-Right"]
    
    for i, radar in enumerate(car.radars):
        dist = radar[1]
        label = labels[i]
        # 排版：左邊一排，右邊一排
        col = i % 2 
        row = i // 2
        x_pos = GAME_WIDTH + 10 + col * 90
        y_pos = y + row * 20
        
        text = f"{label}: {dist}"
        # 如果距離過近，數據變紅警告
        data_color = RED if dist < 50 and show_radar else text_color
        
        screen.blit(lidar_font.render(text, True, data_color), (x_pos, y_pos))

    # 按鈕
    btn_color = (0, 150, 0) if show_radar else (150, 0, 0)
    btn_rect = pygame.Rect(GAME_WIDTH + 20, HEIGHT - 60, 160, 40)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=5)
    btn_text = font.render(f"Lidar: {'ON' if show_radar else 'OFF'} (L)", True, WHITE)
    screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
    
    return btn_rect

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("AI Traffic Sim - Phase I (360 Vision)")
    clock = pygame.time.Clock()

    player_car = Car(GAME_WIDTH // 2, HEIGHT - 150)
    
    walls = [
        pygame.Rect(0, 0, ROAD_X, HEIGHT),
        pygame.Rect(ROAD_X + ROAD_WIDTH, 0, GAME_WIDTH - (ROAD_X + ROAD_WIDTH), HEIGHT)
    ]
    
    npcs = []
    lane_offset = 0
    spawn_timer = 0
    crash_timer = 0 
    TRAFFIC_START_DIST = 10000 
    
    show_radar = True
    btn_rect = pygame.Rect(0, 0, 0, 0)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: 
                    player_car = Car(GAME_WIDTH // 2, HEIGHT - 150)
                    npcs.clear()
                    lane_offset = 0
                    crash_timer = 0
                if event.key == pygame.K_l: 
                    show_radar = not show_radar
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    if btn_rect.collidepoint(event.pos):
                        show_radar = not show_radar

        player_car.handle_input()
        
        if player_car.alive:
            lane_offset += player_car.speed 
            # 支援倒車的背景捲動 (如果是負速，offset 會減少，看起來像往後退)
            if lane_offset >= 40: lane_offset = 0
            if lane_offset < 0: lane_offset = 40 # 處理倒車循環
            
            if player_car.distance_traveled > TRAFFIC_START_DIST:
                spawn_timer += 1
                if spawn_timer > 40 and random.random() < 0.05:
                    lane = random.randint(0, NUM_LANES - 1)
                    npc_speed = random.uniform(5, 12)
                    
                    spawn_y = -100 
                    if npc_speed > player_car.speed + 5: 
                         spawn_y = HEIGHT + 100
                    else:
                         spawn_y = -100

                    safe = True
                    for npc in npcs:
                        if abs(npc.rect.centerx - (ROAD_X + (lane * LANE_WIDTH) + (LANE_WIDTH // 2))) < 10:
                            if abs(npc.rect.y - spawn_y) < 200:
                                safe = False
                                break
                    
                    if safe:
                        npcs.append(NPC_Car(lane, spawn_y, npc_speed))
                        spawn_timer = 0
            
            for npc in npcs[:]:
                npc.update(player_car, npcs)
                if npc.rect.y > HEIGHT + 2000 or npc.rect.y < -300:
                    npcs.remove(npc)
        else:
            crash_timer += 1
            if crash_timer > 30: 
                player_car = Car(GAME_WIDTH // 2, HEIGHT - 150)
                npcs.clear()
                lane_offset = 0
                crash_timer = 0

        player_car.update(walls, npcs)

        screen.fill(BLACK) 
        
        # 畫背景
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, ROAD_X, HEIGHT))
        pygame.draw.rect(screen, (34, 139, 34), (ROAD_X + ROAD_WIDTH, 0, GAME_WIDTH - (ROAD_X + ROAD_WIDTH), HEIGHT))
        
        pygame.draw.line(screen, WHITE, (ROAD_X, 0), (ROAD_X, HEIGHT), 5)
        pygame.draw.line(screen, WHITE, (ROAD_X + ROAD_WIDTH, 0), (ROAD_X + ROAD_WIDTH, HEIGHT), 5)
        
        for i in range(1, NUM_LANES):
            x = ROAD_X + i * LANE_WIDTH
            for y in range(-50, HEIGHT, 40):
                draw_y = y + lane_offset
                if draw_y > HEIGHT: draw_y -= (HEIGHT + 50)
                pygame.draw.line(screen, WHITE, (x, draw_y), (x, draw_y + 20), 2)

        for npc in npcs:
            npc.draw(screen)
            
        player_car.draw(screen, show_radar)
        
        btn_rect = draw_sidebar(screen, player_car, show_radar)

        if not player_car.alive:
            font = pygame.font.SysFont('Arial', 50, bold=True)
            text = font.render('CRASHED!', True, RED)
            text_rect = text.get_rect(center=(GAME_WIDTH//2, HEIGHT//2))
            
            bg_rect = text_rect.inflate(20, 20)
            s = pygame.Surface((bg_rect.width, bg_rect.height))
            s.set_alpha(200)
            s.fill(BLACK)
            screen.blit(s, bg_rect)
            screen.blit(text, text_rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()