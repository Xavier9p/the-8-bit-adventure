import pgzrun, random, time, pygame, json, os
from pygame import Rect
from pgzero.actor import Actor

WIDTH, HEIGHT, TITLE = 960, 540, "'A aventura de 8 bits'"
SCALE_FACTOR = HEIGHT / 600
GRAVITY, JUMP_STRENGTH = 0.5 * SCALE_FACTOR, -9.5 * SCALE_FACTOR
SPEED, CLIMB_SPEED, BULLET_SPEED = 4 * SCALE_FACTOR, 3 * SCALE_FACTOR, 7 * SCALE_FACTOR
TILE_W, TILE_H, KNOCKBACK_X, KNOCKBACK_Y = WIDTH / 24, HEIGHT / 10, 4 * SCALE_FACTOR, -3.2 * SCALE_FACTOR
MAX_LIVES, INVUL_TIME, BLINK_DUR, BLINK_INT, STUN_TIME = 5, 0.7, 0.5, 0.1, 0.25
TOTAL_ENEMIES_GOAL = 29
game_state, current_level, max_levels, music_on, game_time = "menu", 1, 5, True, 0.0
player_name_input, new_high_score = "", False
platforms, ladders, bullets, enemies, door = [], [], [], [], None
background_surface, asset_ladder, asset_floor, asset_door, img_star, img_star_empty = None, None, None, None, None, None
img_menu_bg, img_pause_bg, img_gameover_bg, img_victory_bg = None, None, None, None
enemies_killed, level_score, final_stars, high_scores = 0, 0, 0, []

LEVELS = [
    ("                        ", "D                       ", "                        ", "D        E       B      ", "  E     B               "),
    ("                        ", "#######  ###   E        ", "    E        B        D ", "#####  ######  #####H###", "H#### ####  ## ###  B  D"),
    ("            B           ", "      #      #####   ##H", " H#### ##  #####  ######", "                    H   ", "H                 ######"),
    ("          H######       ", "      #                H", " H     B         E      ", "   E              B H   ", "H              B        "),
    ("          H     #       ", "      #                H", " H    ##### #########   ", " ##### #####H  #########", "H    ###  ###H####      "),
    ("     #H###H     #   B   ", "      ####H      B  ####", " H           B          ", "            H           ", "H            H          "),
    ("   E  H         #H######", "          H   ######    ", " #### #### #### ####H   ", "      B     H   E       ", "####       E H     B    "),
    ("  H####          H      ", "       E  H       B     ", "                    H   ", "P    ####   ######H#####", "        #######H#####   "),
    ("P H              H     D", "P   #######   ######### ", "P   E  ######    E  ####", "####       B      H     ", "P          E   H   B    "),
    ("######          ########", "###                     ", "######        ######    ", "      #############     ", "########################")
]
def load_scores():
    global high_scores
    if os.path.exists("scores.json"):
        try:
            with open("scores.json", "r") as f: high_scores = json.load(f)
        except: high_scores = []
    if not high_scores: high_scores = []
    high_scores.sort(key=lambda x: x[1], reverse=True); high_scores = high_scores[:5]
def save_scores():
    with open("scores.json", "w") as f: json.dump(high_scores, f)
def check_high_score(score):
    return True
def add_score(name, score):
    global high_scores
    high_scores.append([name, score])
    high_scores.sort(key=lambda x: x[1], reverse=True)
    save_scores()
def manage_audio(type, name=None):
    if type == "music":
        if music_on and not music.is_playing("music_bg"):
            try: music.play("music_bg"); music.set_volume(0.56)
            except: pass
        elif not music_on: music.stop()
    elif type == "sfx":
        try:
            snd = getattr(sounds, name if hasattr(sounds, name) else 'shoot')
            vol = 0.3 if name == "shoot_enemy" else 0.6 if name in ["shoot", "player"] else 0.25 if name == "explosion" else 2.0 if name == "jump" else 0.87
            snd.set_volume(vol); snd.play()
        except: pass
def init_assets():
    global asset_ladder, asset_floor, asset_door, img_star, img_star_empty
    global img_menu_bg, img_pause_bg, img_gameover_bg, img_victory_bg
    load_scores()
    img_star = pygame.transform.smoothscale(pygame.image.load("images/star.png"), (60, 60))
    img_star_empty = pygame.transform.smoothscale(pygame.image.load("images/star_empty.png"), (60, 60))
    asset_ladder = pygame.transform.smoothscale(pygame.image.load("images/block_ladder.png"), (int(TILE_W), int(TILE_H)))
    asset_floor = pygame.transform.scale(pygame.image.load("images/block_floor.png"), (int(TILE_W), int(TILE_H)))
    asset_door = pygame.transform.scale(pygame.image.load("images/door.png"), (int(TILE_W), int(TILE_H * 1.15)+2))
    try:
        img_menu_bg = pygame.transform.scale(pygame.image.load("images/menu_bg.png"), (WIDTH, HEIGHT))
        img_pause_bg = pygame.transform.scale(pygame.image.load("images/pause_bg.png"), (WIDTH, HEIGHT))
        img_gameover_bg = pygame.transform.scale(pygame.image.load("images/gameover_bg.png"), (WIDTH, HEIGHT))
        img_victory_bg = pygame.transform.scale(pygame.image.load("images/victory_bg.png"), (WIDTH, HEIGHT))
    except: pass
class AnimatedSprite(Actor):
    def __init__(self, img_base, pos, frames=2, scale_to_tile=True, scale_mult=1.0):
        super().__init__(img_base + "_idle1", pos)
        self.img_base, self.frames, self.frame_timer, self.current_frame = img_base, frames, 0, 1
        self.facing_right, self.scale_to_tile, self.scale_mult = True, scale_to_tile, scale_mult
        self._resize_current_image()
    def _resize_current_image(self):
        target_h = int(TILE_H * 0.75 * self.scale_mult)
        orig = pygame.image.load(f"images/{self.image}.png"); new_w = int(target_h * (orig.get_width() / orig.get_height()))
        scaled = pygame.transform.scale(orig, (new_w, target_h))
        if not self.facing_right: scaled = pygame.transform.flip(scaled, True, False)
        self._surf = scaled; self._update_pos()
    def animate(self, action="idle"):
        self.frame_timer += 1
        if self.frame_timer > 10: self.frame_timer = 0; self.current_frame = 1 if self.current_frame >= self.frames else self.current_frame + 1
        self.image = f"{self.img_base}_{action}{self.current_frame}"
        if self.scale_to_tile: self._resize_current_image()

class Player(AnimatedSprite):
    def __init__(self, pos, hp):
        super().__init__("alien", pos, frames=2, scale_to_tile=True, scale_mult=1.2)
        self.vx, self.vy, self.on_ground, self.is_climbing = 0, 0, False, False
        self.hp, self.invul_timer, self.stun_timer = hp, 0, 0
        self.hitbox = Rect(pos[0], pos[1], TILE_W * 0.6, TILE_H * 0.72); self.hitbox.center = pos
    def update_player(self, dt):
        if self.invul_timer > 0: self.invul_timer -= dt
        if self.stun_timer > 0: self.stun_timer -= dt
        if self.stun_timer <= 0:
            if keyboard.d: self.vx, self.facing_right = SPEED, True; self.animate("walk")
            elif keyboard.a: self.vx, self.facing_right = -SPEED, False; self.animate("walk")
            else: self.vx = 0; self.animate("idle")
            touching_ladder = self.hitbox.collidelist(ladders) != -1
            if touching_ladder and (keyboard.w or keyboard.s): self.is_climbing = True
            elif not touching_ladder: self.is_climbing = False
            if self.is_climbing:
                if keyboard.w: self.vy = -CLIMB_SPEED; self.animate("climb")
                elif keyboard.s: self.vy = CLIMB_SPEED; self.animate("climb")
                else: self.vy = 0
            else:
                if keyboard.space and self.on_ground: self.vy, self.on_ground = JUMP_STRENGTH, False; manage_audio("sfx", "jump")
                self.vy += GRAVITY
        self.hitbox.x += self.vx
        if (idx := self.hitbox.collidelist(platforms)) != -1: 
            if self.vx > 0: self.hitbox.right = platforms[idx].left
            if self.vx < 0: self.hitbox.left = platforms[idx].right
        self.hitbox.y += self.vy
        if (idx := self.hitbox.collidelist(platforms)) != -1:
            if self.vy > 0: self.hitbox.bottom, self.vy, self.on_ground, self.is_climbing = platforms[idx].top, 0, True, False
            elif self.vy < 0: self.hitbox.top, self.vy = platforms[idx].bottom, 0
        else:
            if not self.is_climbing: self.on_ground = False
        self.hitbox.x = max(0, min(self.hitbox.x, WIDTH - self.hitbox.width)); self.x, self.bottom = self.hitbox.centerx, self.hitbox.bottom
        if self.hitbox.y > HEIGHT + 50: take_damage(1); reset_position() if self.hp > 0 else None
class Enemy(AnimatedSprite):
    def __init__(self, pos, color_variant):
        super().__init__(f"enemy_{color_variant}", pos, frames=2, scale_to_tile=True, scale_mult=1.0)
        self.vx, self.reload_timer, self.patrol_min, self.patrol_max = 2 * SCALE_FACTOR, 0, 0, WIDTH 
    def update_enemy(self):
        self.animate("walk"); self.x += self.vx
        if self.vx > 0 and self.x >= self.patrol_max: self.x, self.vx, self.facing_right = self.patrol_max, self.vx * -1, False
        elif self.vx < 0 and self.x <= self.patrol_min: self.x, self.vx, self.facing_right = self.patrol_min, self.vx * -1, True
        self.reload_timer += 1
        if self.reload_timer > 100 and random.random() < 0.0635: shoot(self.x, self.y, 1 if self.facing_right else -1, "enemy"); self.reload_timer = 0
def generate_background_surface(lvl_idx):
    surf = pygame.Surface((WIDTH, HEIGHT))
    tile = pygame.image.load(f"images/bg_{lvl_idx}.png")
    for x in range(0, WIDTH, 32):
        for y in range(0, HEIGHT, 32): surf.blit(tile, (x, y))
    return surf
def calculate_enemy_patrols():
    for e in enemies:
        check_y, min_x, max_x = e.y + TILE_H, e.x, e.x
        while True:
            test_rect = Rect(min_x - TILE_W, check_y - 10, 5, 5)
            if test_rect.collidelist(platforms) != -1 and test_rect.collidelist(ladders) == -1: min_x -= TILE_W
            else: min_x = max(0, min_x - TILE_W/2); break
        while True:
            test_rect = Rect(max_x + TILE_W, check_y - 10, 5, 5)
            if test_rect.collidelist(platforms) != -1 and test_rect.collidelist(ladders) == -1: max_x += TILE_W
            else: max_x = min(WIDTH, max_x + TILE_W/2); break
        e.patrol_min, e.patrol_max = min_x, max_x - 12
def load_level(idx, hp=None):
    global player, door, background_surface, enemies_killed
    platforms.clear(); ladders.clear(); enemies.clear(); bullets.clear(); background_surface = generate_background_surface(idx)
    for r in range(10): 
        row_str = LEVELS[r][idx-1] 
        for c, char in enumerate(row_str):
            x, y = c * TILE_W + TILE_W/2, r * TILE_H + TILE_H/2
            if char == "#": platforms.append(Rect(c*TILE_W, r*TILE_H, TILE_W, TILE_H))
            elif char == "H": ladders.append(Rect(c*TILE_W, r*TILE_H, TILE_W, TILE_H))
            elif char == "P": player = Player((x, y), MAX_LIVES if hp is None else hp)
            elif char == "D": 
                door = Actor("door", (x-13, y - 21))
                door._surf = asset_door
            elif char in ["E", "B"]: enemies.append(Enemy((x, y), "pink" if char=="E" else "blue"))
    calculate_enemy_patrols()
def take_damage(amount, source=None):
    global game_state
    if player.invul_timer > 0: return
    player.hp -= amount; manage_audio("sfx", "explosion"); player.invul_timer, player.stun_timer = INVUL_TIME, STUN_TIME
    if source and not player.is_climbing: 
        direction = -1 if player.hitbox.centerx < source.x else 1
        player.vx, player.vy, player.on_ground, player.is_climbing = KNOCKBACK_X * direction, KNOCKBACK_Y, False, False
        player.x, player.bottom = player.hitbox.centerx, player.hitbox.bottom
    if player.hp <= 0: game_state = "game_over"

def shoot(x, y, d, owner):
    bullets.append(Actor("laser", (x, y))); bullets[-1].direction, bullets[-1].owner = d, owner
    manage_audio("sfx", "shoot_enemy" if owner == "enemy" else "shoot")
def reset_position(): load_level(current_level, player.hp)
def calculate_final_score():
    global level_score, final_stars, new_high_score, player_name_input
    s_lives = (player.hp / MAX_LIVES) * 3334
    s_enemies = (min(enemies_killed, TOTAL_ENEMIES_GOAL) / TOTAL_ENEMIES_GOAL) * 3333
    s_time = 3333 if game_time <= 30 else (max(0, 420 - game_time) / 390) * 3333
    level_score = int(s_lives + s_enemies + s_time)
    final_stars = 0 
    if enemies_killed >= TOTAL_ENEMIES_GOAL:
        final_stars += 1
    if player.hp >= MAX_LIVES:
        final_stars += 1
    if game_time <= 90:
        final_stars += 1
    new_high_score = True
    player_name_input = ""
def next_level(): 
    global current_level, game_state
    if current_level == max_levels: calculate_final_score(); game_state = "victory"
    else: current_level += 1; load_level(current_level, player.hp); game_state = "playing"
def restart_game(): 
    global current_level, game_time, game_state, enemies_killed
    current_level, game_time, enemies_killed = 1, 0.0, 0
    load_level(1, MAX_LIVES); game_state = "playing"
init_assets(); load_level(current_level); btns = [Actor("ui_button", (WIDTH/2, HEIGHT/2 + o)) for o in [-40, 40, 120]]
def update(dt):
    global game_state, current_level, game_time, enemies_killed
    manage_audio("music")
    if game_state == "playing":
        game_time += dt; player.update_player(dt)
        for e in enemies: e.update_enemy()
        if door:
            door_hitbox = door._rect.inflate(-door.width * 0.3, 0).move(10, +10)
            if player.hitbox.colliderect(door_hitbox): next_level()
        for e in enemies:
            if player.hitbox.colliderect(e._rect): take_damage(1, e)
        for b in bullets[:]:
            b.x += BULLET_SPEED if b.direction == 1 else -BULLET_SPEED
            if b.x < 0 or b.x > WIDTH or b.collidelist(platforms) != -1: bullets.remove(b); continue
            if b.owner == "enemy" and player.hitbox.colliderect(b._rect): take_damage(1, b); bullets.remove(b) if b in bullets else None
            elif b.owner == "player" and (idx := b.collidelist(enemies)) != -1: enemies.pop(idx); bullets.remove(b); manage_audio("sfx", "explosion"); enemies_killed += 1
def draw_colored_text(parts, y_pos, start_x=20, font_size=40):
    current_x = start_x; font = pygame.font.SysFont(None, int(font_size * 1.3))
    for text, color in parts: screen.draw.text(text, (current_x, y_pos), fontsize=font_size, color=color); current_x += font.size(text)[0] * 0.8
def draw_victory_screen():
    panel_rect = Rect((WIDTH-600)//2, (HEIGHT-400)//2, 600, 400)
    screen.draw.filled_rect(panel_rect, (30, 30, 50)); screen.draw.rect(panel_rect, "white")
    screen.draw.text("MISSÃO CUMPRIDA!", center=(WIDTH/2, panel_rect.y + 40), fontsize=50, color="yellow")
    star_cx, star_y, star_sp = WIDTH / 2, panel_rect.y + 100, 60
    for i in range(3):
        pos = (star_cx + (i - 1) * star_sp - 30, star_y - 30)
        screen.blit(img_star if i < final_stars else img_star_empty, pos)
    sx, sy, lh = panel_rect.x + 50, panel_rect.y + 140, 35
    screen.draw.text(f"Inimigos ({enemies_killed}/{TOTAL_ENEMIES_GOAL}):  +{int((min(enemies_killed, TOTAL_ENEMIES_GOAL)/TOTAL_ENEMIES_GOAL)*3333)}", (sx, sy), fontsize=25, color="white")
    screen.draw.text(f"Vidas ({player.hp}/{MAX_LIVES}):     +{int((player.hp/MAX_LIVES)*3334)}", (sx, sy + lh), fontsize=25, color="white")
    st = 3333 if game_time <= 30 else int((max(0, 420-game_time)/390)*3333)
    screen.draw.text(f"Tempo:             +{st}", (sx, sy + lh*2), fontsize=25, color="white")
    screen.draw.line((sx, sy + lh*3), (sx + 180, sy + lh*3), "white")
    screen.draw.text(f"TOTAL: {level_score}", (sx, sy + lh*3 + 10), fontsize=40, color="yellow")
    cnx, csx, hy = panel_rect.right - 190, panel_rect.right - 70, sy
    screen.draw.text("NOME", center=(cnx, hy), fontsize=22, color="gray"); screen.draw.text("SCORE", center=(csx, hy), fontsize=22, color="gray")
    screen.draw.line((cnx - 30, hy + 15), (csx + 30, hy + 15), "white")
    for i, (name, pts) in enumerate(high_scores[:5]):
        y = hy + 35 + (i * 25); screen.draw.text(f"{i+1}. {name}", center=(cnx, y), fontsize=22, color="white"); screen.draw.text(f"{pts}", center=(csx, y), fontsize=22, color="yellow")
    if new_high_score:
        blink = "_" if int(time.time()*2)%2==0 else " "
        screen.draw.text(f"NOVO RECORDE! Digite: {player_name_input}{blink}", center=(WIDTH/2, panel_rect.bottom - 70), fontsize=25, color="cyan")
        screen.draw.text("'Enter' para salvar", center=(WIDTH/2, panel_rect.bottom - 40), fontsize=20, color="white")
    else: 
        screen.draw.text("'Enter' para continuar", center=(WIDTH/2, panel_rect.bottom - 40), fontsize=22, color="white")
def draw():
    screen.clear()
    if game_state == "menu":
        if img_menu_bg: screen.blit(img_menu_bg, (0, 0))
        screen.draw.text(TITLE, center=(WIDTH/2, HEIGHT/4), fontsize=60, color="orange")
        for i, t in enumerate(["INICIAR", f"MÚSICA: {'ON' if music_on else 'OFF'}", "SAIR"]): btns[i].draw(); screen.draw.text(t, center=btns[i].pos, fontsize=30, color="white")
        if len(high_scores) > 0:
            top_name, top_score = high_scores[0][0], str(high_scores[0][1])
            draw_colored_text([("1º Lugar: ", "yellow"), (top_name, "white"), (" |", "yellow")], HEIGHT - 70, 20, font_size=26)
            draw_colored_text([("Score:    ", "yellow"), (top_score, "white"), (" |", "yellow")], HEIGHT - 45, 20, font_size=26)
    elif game_state == "playing":
        if background_surface: screen.blit(background_surface, (0, 0))
        for obj in platforms + ladders + enemies + bullets: 
            if isinstance(obj, Rect):
                if obj in platforms: screen.blit(asset_floor, obj)
                else: screen.blit(asset_ladder, (obj.centerx - asset_ladder.get_width() // 2, obj.y))
            else: obj.draw()
        if door: door.draw()
        if not (player.invul_timer > 0 and (INVUL_TIME - player.invul_timer) < BLINK_DUR and int(game_time / BLINK_INT) % 2 == 0): player.draw()
        screen.draw.text(f"HP: {player.hp}", (20, 10), fontsize=35, color="red"); screen.draw.text(f"LVL: {current_level}/{max_levels}", (WIDTH-150, 10), fontsize=35, color="yellow");
        screen.draw.text(f"TIME: {int(game_time)}s", (WIDTH/2-50, 10), fontsize=35, color="white")
    elif game_state == "paused":
        if img_pause_bg: screen.blit(img_pause_bg, (0, 0))
        screen.draw.text("PAUSADO", center=(WIDTH/2, HEIGHT/4), fontsize=60, color="white")
        for i, t in enumerate(["CONTINUAR", f"MÚSICA: {'ON' if music_on else 'OFF'}", "SAIR"]): btns[i].draw(); screen.draw.text(t, center=btns[i].pos, fontsize=30, color="white")
    elif game_state == "game_over":
        if img_gameover_bg: screen.blit(img_gameover_bg, (0, 0))
        screen.draw.text("VOCÊ PERDEU", center=(WIDTH/2, HEIGHT/3), fontsize=70, color="red")
        btns[1].draw(); screen.draw.text("TENTE NOVAMENTE", center=btns[1].pos, fontsize=28, color="white")
        if int(time.time() * 2) % 2 == 0: screen.draw.text("ou pressione 'ESC' para Menu", center=(WIDTH/2, HEIGHT/2 + 120), fontsize=25, color="yellow")

    elif game_state == "victory":
        if img_victory_bg: screen.blit(img_victory_bg, (0, 0))
        draw_victory_screen()
def on_mouse_down(pos):
    global game_state, music_on
    if game_state in ["menu", "paused"]:
        if btns[0].collidepoint(pos): restart_game() if game_state == "menu" else globals().update(game_state="playing")
        elif btns[1].collidepoint(pos): music_on = not music_on
        elif btns[2].collidepoint(pos): exit()
    elif game_state == "playing": shoot(player.x, player.y + 15, 1 if player.facing_right else -1, "player")
    elif game_state == "game_over" and btns[1].collidepoint(pos): restart_game()
def on_key_down(key):
    global game_state, player_name_input, new_high_score
    if game_state == "victory" and new_high_score:
        if key == keys.RETURN:
            if len(player_name_input) > 0: add_score(player_name_input, level_score); new_high_score = False; game_state = "menu"
        elif key == keys.BACKSPACE: player_name_input = player_name_input[:-1]
        elif len(player_name_input) < 3 and hasattr(key, 'name') and len(key.name) == 1: 
            try: char = chr(key.value).upper() 
            except: char = ""
            if char.isalnum(): player_name_input += char
        return
    if key == keys.ESCAPE: 
        if game_state == "victory": exit()
        game_state = "paused" if game_state == "playing" else "playing" if game_state == "paused" else "menu"
    if game_state == "playing" and key == keys.RETURN: shoot(player.x, player.y + 15, 1 if player.facing_right else -1, "player")
    if (game_state == "game_over" or (game_state == "victory" and not new_high_score)) and key == keys.RETURN: restart_game()
pgzrun.go()