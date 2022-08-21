from matplotlib.colors import LightSource
import pygame
import sys
import os
import random
from pygame.locals import *
from pyrsistent import s

# general setup
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 256)
pygame.mixer.set_num_channels(64)

def load_sound(path):
    class NoneSound:
        def play(self):
            pass

    if not pygame.mixer:
        return NoneSound()
    full_path = os.path.join('sfx', path)
    try:
        sound = pygame.mixer.Sound(full_path)
    except pygame.error as message:
        print('cannot load sound: ' + full_path)
        raise SystemExit(message)

    return sound


def load_image(path, color_key=None):
    full_path = os.path.join('assets/images', path)
    try:
        image = pygame.image.load(full_path)
    except pygame.error as message:
        print('cannot load image: ' + full_path)
        raise SystemExit(message)
    image = image.convert()

    if color_key is not None:
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key, RLEACCEL)

    return image, image.get_rect()

# setting up main window
SCREEN_SIZE = [960, 540]
screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)
pygame.display.set_caption('Ping Pong')

#Materials and Assets
ball_hit_sfx = load_sound('ball_hit.wav')
ball_bounce_sfx = load_sound('ball_bounce.wav')
ball_restart_sfx = load_sound('ball_restart.wav')
game_font = pygame.font.Font("freesansbold.ttf", 32)
bg_color = (30, 39, 46)
primary_color = (211, 84, 0)
blue = (116, 185, 255)

class Block(pygame.sprite.Sprite):
    def __init__(self, size, position , image_path=None):
        super().__init__()
        # self.image = load_image(image_path)
        # self.rect = self.image.get_rect(center = position)
        self.rect = pygame.Rect(position, size)
        self.image = pygame.Surface(size)
        self.image.fill(primary_color)

class Player(Block):
    def __init__(self, size, position, speed, image_path=None):
        super().__init__(size, position, image_path)
        self.speed = speed
        self.movement = 0
    
    def screen_constrain(self):
        if self.rect.top <= 0:
            self.rect.top = 0
        if self.rect.bottom >= SCREEN_SIZE[1]:
            self.rect.bottom = SCREEN_SIZE[1]

    def update(self, ball_group):
        self.rect.y += self.movement
        self.screen_constrain()

class Opponent(Block):
    def __init__(self,size, position, speed, image_path=None):
        super().__init__(size, position, image_path)
        self.speed = speed
        self.movement = 0

    def screen_constrain(self):
        if self.rect.top <= 0:
            self.rect.top = 0
        if self.rect.bottom >= SCREEN_SIZE[1]:
            self.rect.bottom = SCREEN_SIZE[1]
    
    def update(self, ball_group):
        if self.rect.top < ball_group.sprite.rect.top:
            self.rect.top += self.speed
        if self.rect.top > ball_group.sprite.rect.top:
            self.rect.top -= 8
        self.screen_constrain()

class Ball(Block):
    def __init__(self, size, position, speed, paddles, image_path=None):
        super().__init__(size, position, image_path)
        self.speed = speed
        self.velocity = [1, 1]
        self.paddles = paddles
        self.active = False
        self.score_time = 0
        self.image.fill(bg_color)
        pygame.draw.circle(self.image, primary_color, (15, 15), 15)

    def update(self):
        if self.active:
            self.rect.x += self.speed[0] * self.velocity[0]
            self.rect.y += self.speed[1] * self.velocity[1]
            self.collision()
        else:
            self.restart_counter()
    
    def collision(self):
        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_SIZE[1]:
            ball_bounce_sfx.play()
            self.speed[1] *= -1
        
        if pygame.sprite.spritecollide(self, self.paddles, False):
            ball_hit_sfx.play()
            collision_paddle = pygame.sprite.spritecollide(self, self.paddles, False)[0].rect
            #only bounce reverse if the ball hit the side of rectangle
            if abs(self.rect.right - collision_paddle.left) < 20: 
                self.velocity[0] *= -1
            if abs(self.rect.left - collision_paddle.right) < 20:
                self.velocity[0] *= -1
            if abs(self.rect.bottom - collision_paddle.top) < 20 and self.velocity[1] > 0: #bounce reverse if the ball hit the top and is going down
                self.velocity[1] *= -1
            if abs(self.rect.top - collision_paddle.bottom) < 20 and self.velocity[1] < 0: #bounce reverse if the ball hit the bottom and is going up
                self.velocity[1] *= -1

    def reset_ball(self):
        self.active = False
        self.speed[0] *= random.choice((-1, 1))
        self.speed[1] *= random.choice((-1, 1))
        self.score_time = pygame.time.get_ticks()
        self.rect.center = (SCREEN_SIZE[0] / 2, SCREEN_SIZE[1] / 2)
        ball_restart_sfx.play()
    
    def restart_counter(self):
        current_time = pygame.time.get_ticks()
        countdown_number = 3
        color = (163, 203, 56)

        if current_time - self.score_time <= 1000:
            countdown_number = 3
        if 1000 < current_time - self.score_time <= 1900:
            countdown_number = 2
            color = (18, 137, 167)
        if 1900 < current_time - self.score_time <= 2100:
            countdown_number = 1
            color = (237, 76, 103)
        if current_time - self.score_time >= 2000:
            self.active = True

        time_counter = game_font.render(str(countdown_number), True, color)
        time_counter_rect = time_counter.get_rect(center = (SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2 + 50))
        pygame.draw.rect(screen, bg_color, time_counter_rect)
        screen.blit(time_counter, time_counter_rect)

class GameManager:
    def __init__(self, ball_group, paddle_group):
        self.player_score = 0
        self.opponent_score = 0
        self.ball_group = ball_group
        self.paddle_group = paddle_group
        self.timer = 0

    def run_game(self):
        self.ball_group.update()
        self.paddle_group.update(self.ball_group)
        self.ball_group.draw(screen)
        self.paddle_group.draw(screen)

        self.reset_ball()
        self.draw_score()

    def reset_ball(self):
        if self.ball_group.sprite.rect.right >= SCREEN_SIZE[0]:
            self.opponent_score += 1
            self.ball_group.sprite.reset_ball()
        if self.ball_group.sprite.rect.right <= 0:
            self.player_score += 1
            self.ball_group.sprite.reset_ball()
    
    def draw_score(self):
        player_score = game_font.render(str(self.player_score), True, blue)
        opponent_score = game_font.render(str(self.opponent_score), True, blue)

        player_score_rect = player_score.get_rect(midleft = (SCREEN_SIZE[0]/2 + 40, SCREEN_SIZE[1]/2))
        opponent_score_rect = player_score.get_rect(midright = (SCREEN_SIZE[0]/2 - 40, SCREEN_SIZE[1]/2))

        screen.blit(player_score, player_score_rect)
        screen.blit(opponent_score, opponent_score_rect)

#Game Objects
player = Player((10, 100), (SCREEN_SIZE[0] - 20, SCREEN_SIZE[1]/2), 7)
opponent = Opponent((10, 100), (10, SCREEN_SIZE[1]/2), 6)
paddle_group = pygame.sprite.Group()
paddle_group.add(player)
paddle_group.add(opponent)

ball = Ball((30, 30), (SCREEN_SIZE[0]/2 - 15, SCREEN_SIZE[1]/2 - 15), [6,6], paddle_group)
ball_sprite = pygame.sprite.GroupSingle()
ball_sprite.add(ball)

game_manager = GameManager(ball_sprite, paddle_group)

def main():
    clock = pygame.time.Clock()
    gameRun = True

    def level_increase():
        cur_time = pygame.time.get_ticks()
        if cur_time - game_manager.timer > 5000:
            if ball.speed[0] <= 12:
                ball.speed = [x+1 for x in ball.speed]
                player.speed += 1
                game_manager.timer = cur_time
    
    # game entities

    #Score Timer
    global score_time
    score_time = True

    while gameRun:
        screen.fill(bg_color)
        pygame.draw.aaline(screen, primary_color, (SCREEN_SIZE[0]/2, 0), (SCREEN_SIZE[0]/2, SCREEN_SIZE[1]))
        player.movement = 0

        # handing input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                gameRun = False

        # handing key inputs
        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN]:
            player.movement = player.speed
        if keys[pygame.K_UP]:
            player.movement = -player.speed
        
        game_manager.run_game()
        level_increase()

        pygame.display.update()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
