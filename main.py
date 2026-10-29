# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["pygame-ce>=2.5,<3"]
# ///
"""Multi-level desktop brick breaker written in Python with Pygame CE."""

import time
import pygame
from physics import ARENA_BOTTOM, ARENA_LEFT, ARENA_RIGHT, ARENA_TOP, HEIGHT, WIDTH, GameState, update_game

WHITE, INK, MUTED, LINE = (255, 255, 255), (37, 40, 45), (119, 124, 132), (224, 226, 230)
BALL_COLOR, PADDLE_COLOR = (255, 116, 83), (53, 58, 65)
BOMB_COLOR, BOMB_CORE = (53, 58, 65), (255, 142, 82)
POWERUP_FILL, POWERUP_COLOR = (225, 242, 235), (63, 145, 101)
BRICK_COLORS = {1: (255, 255, 255), 2: (247, 166, 181)}
BRICK_BORDERS = {1: (194, 199, 207), 2: (218, 105, 127)}
STEP = 1 / 120


def draw_centered(surface, font, text, y, color=INK):
    image = font.render(text, True, color)
    surface.blit(image, image.get_rect(center=(WIDTH // 2, y)))


def draw_game(screen, state, fonts):
    screen.fill(WHITE)
    screen.blit(fonts["title"].render("BREAK / OUT", True, INK), (int(ARENA_LEFT), 24))
    score = fonts["body"].render(f"SCORE  {state.score:04d}", True, INK)
    lives = fonts["body"].render(f"LIVES  {state.lives}", True, INK)
    level = fonts["body"].render(f"LEVEL  {state.level + 1}", True, INK)
    screen.blit(score, (int(ARENA_RIGHT - score.get_width()), 29))
    screen.blit(lives, (int(ARENA_RIGHT - lives.get_width()), 58))
    screen.blit(level, (int(ARENA_LEFT), 61))
    pygame.draw.lines(screen, LINE, False, [(ARENA_LEFT, ARENA_BOTTOM), (ARENA_LEFT, ARENA_TOP), (ARENA_RIGHT, ARENA_TOP), (ARENA_RIGHT, ARENA_BOTTOM)], 2)
    for brick in state.bricks:
        if brick.alive:
            rect = pygame.Rect(round(brick.x), round(brick.y), round(brick.width), round(brick.height))
            color = BRICK_COLORS.get(brick.hits_left, BRICK_COLORS[2])
            border = BRICK_BORDERS.get(brick.hits_left, BRICK_BORDERS[2])
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, border, rect, 2, border_radius=5)
    if state.explosions:
        effects = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for explosion in state.explosions:
            progress = explosion.progress
            radius = round(10 + (explosion.max_radius - 10) * progress)
            alpha = round(190 * (1 - progress))
            center = round(explosion.x), round(explosion.y)
            pygame.draw.circle(effects, (255, 174, 94, max(0, alpha // 3)), center, radius)
            pygame.draw.circle(effects, (255, 116, 83, max(0, alpha)), center, radius, 5)
            if radius > 20:
                pygame.draw.circle(effects, (255, 210, 122, max(0, alpha // 2)), center, radius - 14, 3)
        screen.blit(effects, (0, 0))
    for powerup in state.powerups:
        center = round(powerup.x), round(powerup.y)
        radius = round(powerup.radius)
        if powerup.kind == "bomb":
            pygame.draw.circle(screen, (255, 236, 220), center, radius)
            pygame.draw.circle(screen, BOMB_CORE, center, radius, 2)
            pygame.draw.circle(screen, BOMB_COLOR, center, radius - 5)
            pygame.draw.circle(screen, BOMB_CORE, (center[0] + 7, center[1] - 7), 3)
            pygame.draw.line(screen, BOMB_CORE, (center[0] + 5, center[1] - 6), (center[0] + 9, center[1] - 11), 2)
        else:
            pygame.draw.circle(screen, POWERUP_FILL, center, radius)
            pygame.draw.circle(screen, POWERUP_COLOR, center, radius, 2)
            pygame.draw.line(screen, POWERUP_COLOR, (center[0] - 6, center[1]), (center[0] + 6, center[1]), 3)
            pygame.draw.line(screen, POWERUP_COLOR, (center[0], center[1] - 6), (center[0], center[1] + 6), 3)
    paddle = pygame.Rect(round(state.paddle.left), round(state.paddle.y), round(state.paddle.width), round(state.paddle.height))
    pygame.draw.rect(screen, PADDLE_COLOR, paddle, border_radius=8)
    for ball in state.balls:
        center = round(ball.x), round(ball.y)
        if ball.kind == "bomb":
            pygame.draw.circle(screen, BOMB_COLOR, center, round(ball.radius + 2))
            pygame.draw.circle(screen, BOMB_CORE, center, 4)
            pygame.draw.line(screen, BOMB_CORE, (center[0] + 5, center[1] - 6), (center[0] + 9, center[1] - 10), 2)
        else:
            pygame.draw.circle(screen, BALL_COLOR, center, round(ball.radius))
            pygame.draw.circle(screen, WHITE, (center[0] - 3, center[1] - 3), 2)
    help_text = "Move: A/D or arrows or mouse    Space/click: launch    P: pause    R: restart"
    help_image = fonts["small"].render(help_text, True, MUTED)
    screen.blit(help_image, help_image.get_rect(center=(WIDTH // 2, HEIGHT - 23)))
    if state.phase == "ready":
        draw_centered(screen, fonts["body"], "PRESS SPACE OR CLICK TO LAUNCH", HEIGHT - 225)
    elif state.phase == "paused":
        draw_centered(screen, fonts["large"], "PAUSED", HEIGHT // 2 + 20)
        draw_centered(screen, fonts["body"], "Press P to continue", HEIGHT // 2 + 59, MUTED)
    elif state.phase in {"won", "game_over"}:
        panel_y = HEIGHT // 2 - 75
        pygame.draw.rect(screen, WHITE, (250, panel_y, 460, 150), border_radius=16)
        pygame.draw.rect(screen, LINE, (250, panel_y, 460, 150), 2, border_radius=16)
        draw_centered(screen, fonts["large"], "LEVEL CLEARED" if state.phase == "won" else "TRY AGAIN", panel_y + 50)
        message = f"Score {state.score} - Press R to play again" if state.phase == "won" else "Press R to restart the level"
        draw_centered(screen, fonts["body"], message, panel_y + 102, MUTED)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Break / Out - HW3")
    clock = pygame.time.Clock()
    fonts = {"title": pygame.font.Font(None, 40), "large": pygame.font.Font(None, 54), "body": pygame.font.Font(None, 28), "small": pygame.font.Font(None, 21)}
    state, accumulator, previous = GameState(), 0.0, time.perf_counter()
    mouse_active, mouse_x, running = False, None, True
    while running:
        now = time.perf_counter()
        frame_seconds, previous = min(now - previous, 0.05), now
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                mouse_active = False
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    state.toggle_pause()
                elif event.key == pygame.K_SPACE:
                    state.launch()
                elif event.key == pygame.K_r:
                    state.restart()
            elif event.type == pygame.MOUSEMOTION:
                mouse_active, mouse_x = True, float(event.pos[0])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_active, mouse_x = True, float(event.pos[0])
                state.launch()
        keys = pygame.key.get_pressed()
        move = float(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - float(keys[pygame.K_LEFT] or keys[pygame.K_a])
        if state.phase != "paused":
            accumulator += frame_seconds
            while accumulator >= STEP:
                update_game(state, STEP, move, mouse_x if mouse_active else None)
                accumulator -= STEP
        draw_game(screen, state, fonts)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()


if __name__ == "__main__":
    main()
