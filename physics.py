"""Testable physics model for the brick breaker.

The Ball class and fixed-step structure are adapted from SD5913 Week 7.
Rendering stays in main.py so this module can be tested without Pygame.
"""

from dataclasses import dataclass, field
import math
import random

WIDTH, HEIGHT = 960, 760
ARENA_LEFT, ARENA_RIGHT = 72.0, WIDTH - 72.0
ARENA_TOP, ARENA_BOTTOM = 96.0, HEIGHT - 54.0
PADDLE_WIDTH, PADDLE_HEIGHT = 132.0, 15.0
PADDLE_Y, PADDLE_SPEED = ARENA_BOTTOM - 33.0, 560.0
BALL_RADIUS, BALL_SPEED = 9.0, 390.0
POWERUP_RADIUS, POWERUP_SPEED = 14.0, BALL_SPEED
POWERUP_DROP_CHANCE, POWERUP_PITY_MISSES = 0.10, 10
EXPLOSION_RADIUS, EXPLOSION_DURATION = 120.0, 0.38
BRICK_COLUMNS = 8
BRICK_GAP, BRICK_HEIGHT = 8.0, 27.0
BRICK_TOP = ARENA_TOP + 52.0

# Each digit is a brick's hit points. Zero would leave an empty space.
# Level 1 has 32 bricks: 20% fewer than the original 5 x 8 board.
# Level 2 uses a 48-brick background board and draws a two-hit heart outline.
LEVELS = (
    (
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ),
    (
        "12211221",
        "21122112",
        "21111112",
        "12111121",
        "11211211",
        "11122111",
    ),
)


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float = BALL_RADIUS
    attached: bool = True
    kind: str = "normal"


@dataclass
class Paddle:
    x: float
    y: float = PADDLE_Y
    width: float = PADDLE_WIDTH
    height: float = PADDLE_HEIGHT

    @property
    def left(self):
        return self.x - self.width / 2

    @property
    def right(self):
        return self.x + self.width / 2


@dataclass
class Brick:
    x: float
    y: float
    width: float
    height: float
    row: int
    column: int
    hits_left: int = 1
    max_hits: int = 1
    alive: bool = True

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height


@dataclass
class PowerUp:
    x: float
    y: float
    kind: str = "multiball"
    vy: float = POWERUP_SPEED
    radius: float = POWERUP_RADIUS


@dataclass
class Explosion:
    x: float
    y: float
    age: float = 0.0
    duration: float = EXPLOSION_DURATION
    max_radius: float = EXPLOSION_RADIUS

    @property
    def progress(self):
        return min(1.0, self.age / self.duration)


def make_bricks(level=0):
    layout = LEVELS[level]
    columns = max(len(line) for line in layout)
    usable = ARENA_RIGHT - ARENA_LEFT
    width = (usable - BRICK_GAP * (columns - 1)) / columns
    bricks = []
    for row, line in enumerate(layout):
        for column, symbol in enumerate(line):
            hits = int(symbol)
            if hits == 0:
                continue
            bricks.append(
                Brick(
                    ARENA_LEFT + column * (width + BRICK_GAP),
                    BRICK_TOP + row * (BRICK_HEIGHT + BRICK_GAP),
                    width,
                    BRICK_HEIGHT,
                    row,
                    column,
                    hits,
                    hits,
                )
            )
    return bricks


@dataclass
class GameState:
    paddle: Paddle = field(default_factory=lambda: Paddle(WIDTH / 2))
    balls: list[Ball] = field(default_factory=list)
    level: int = 0
    bricks: list[Brick] = field(default_factory=list)
    powerups: list[PowerUp] = field(default_factory=list)
    explosions: list[Explosion] = field(default_factory=list)
    missed_powerup_drops: int = 0
    missed_bomb_drops: int = 0
    score: int = 0
    lives: int = 3
    phase: str = "ready"

    def __post_init__(self):
        if not self.balls:
            self.balls = [Ball(WIDTH / 2, PADDLE_Y - BALL_RADIUS - 2, 0, 0)]
        if not self.bricks:
            self.bricks = make_bricks(self.level)

    @property
    def ball(self):
        """The first ball, kept as a convenience for launch logic and tests."""
        return self.balls[0]

    def reset_ball(self):
        self.paddle.x = WIDTH / 2
        self.balls = [Ball(self.paddle.x, self.paddle.y - BALL_RADIUS - 2, 0, 0)]
        self.powerups = []
        self.explosions = []
        self.phase = "ready"

    def restart(self):
        self.level = 0
        self.paddle = Paddle(WIDTH / 2)
        self.bricks = make_bricks(self.level)
        self.missed_powerup_drops = 0
        self.missed_bomb_drops = 0
        self.score, self.lives = 0, 3
        self.reset_ball()

    def launch(self):
        if self.phase != "ready":
            return
        angle = math.radians(53)
        self.ball.vx = BALL_SPEED * math.cos(angle)
        self.ball.vy = -BALL_SPEED * math.sin(angle)
        self.ball.attached = False
        self.phase = "playing"

    def toggle_pause(self):
        if self.phase == "playing":
            self.phase = "paused"
        elif self.phase == "paused":
            self.phase = "playing"


def clamp(value, low, high):
    return max(low, min(high, value))


def circle_hits_rect(circle, left, top, right, bottom):
    dx = circle.x - clamp(circle.x, left, right)
    dy = circle.y - clamp(circle.y, top, bottom)
    return dx * dx + dy * dy <= circle.radius * circle.radius


def reflect_from_brick(ball, brick, previous_x, previous_y):
    if previous_y + ball.radius <= brick.y and ball.vy > 0:
        ball.y, ball.vy = brick.y - ball.radius, -abs(ball.vy)
    elif previous_y - ball.radius >= brick.bottom and ball.vy < 0:
        ball.y, ball.vy = brick.bottom + ball.radius, abs(ball.vy)
    elif previous_x + ball.radius <= brick.x and ball.vx > 0:
        ball.x, ball.vx = brick.x - ball.radius, -abs(ball.vx)
    elif previous_x - ball.radius >= brick.right and ball.vx < 0:
        ball.x, ball.vx = brick.right + ball.radius, abs(ball.vx)
    else:
        horizontal = min(abs(ball.x - brick.x), abs(brick.right - ball.x))
        vertical = min(abs(ball.y - brick.y), abs(brick.bottom - ball.y))
        if horizontal < vertical:
            ball.vx, ball.x = -ball.vx, previous_x
        else:
            ball.vy, ball.y = -ball.vy, previous_y


def bounce_from_paddle(ball, paddle, previous_y):
    if ball.vy <= 0 or previous_y + ball.radius > paddle.y + 4:
        return
    if not circle_hits_rect(ball, paddle.left, paddle.y, paddle.right, paddle.y + paddle.height):
        return
    ball.y = paddle.y - ball.radius
    offset = clamp((ball.x - paddle.x) / (paddle.width / 2), -1.0, 1.0)
    ball.vx = BALL_SPEED * offset * 0.88
    ball.vy = -math.sqrt(max(1.0, BALL_SPEED**2 - ball.vx**2))


def spawn_mirrored_ball(state, kind="normal"):
    source = next((ball for ball in state.balls if not ball.attached), None)
    if source is None:
        return
    state.balls.append(
        Ball(
            source.x,
            source.y,
            -source.vx,
            source.vy,
            source.radius,
            False,
            kind,
        )
    )


def should_drop_powerup(state, kind="multiball"):
    """Apply an independent 10% roll and 10-miss guarantee per item type."""
    counter_name = "missed_bomb_drops" if kind == "bomb" else "missed_powerup_drops"
    misses = getattr(state, counter_name)
    if misses >= POWERUP_PITY_MISSES:
        setattr(state, counter_name, 0)
        return True
    if random.random() < POWERUP_DROP_CHANCE:
        setattr(state, counter_name, 0)
        return True
    setattr(state, counter_name, misses + 1)
    return False


def hit_brick(state, brick):
    brick.hits_left -= 1
    if brick.hits_left > 0:
        return
    brick.alive = False
    state.score += 100
    center_x = brick.x + brick.width / 2
    center_y = brick.y + brick.height / 2
    if should_drop_powerup(state, "multiball"):
        state.powerups.append(PowerUp(center_x, center_y, "multiball"))
    if state.level >= 1 and should_drop_powerup(state, "bomb"):
        state.powerups.append(PowerUp(center_x, center_y, "bomb"))


def explode_bomb(state, ball):
    state.explosions.append(Explosion(ball.x, ball.y))
    radius_squared = EXPLOSION_RADIUS**2
    for brick in state.bricks:
        if not brick.alive:
            continue
        center_x = brick.x + brick.width / 2
        center_y = brick.y + brick.height / 2
        if (center_x - ball.x) ** 2 + (center_y - ball.y) ** 2 <= radius_squared:
            hit_brick(state, brick)


def update_ball(state, ball, seconds):
    previous_x, previous_y = ball.x, ball.y
    ball.x += ball.vx * seconds
    ball.y += ball.vy * seconds
    if ball.x - ball.radius < ARENA_LEFT:
        ball.x, ball.vx = ARENA_LEFT + ball.radius, abs(ball.vx)
    elif ball.x + ball.radius > ARENA_RIGHT:
        ball.x, ball.vx = ARENA_RIGHT - ball.radius, -abs(ball.vx)
    if ball.y - ball.radius < ARENA_TOP:
        ball.y, ball.vy = ARENA_TOP + ball.radius, abs(ball.vy)

    bounce_from_paddle(ball, state.paddle, previous_y)
    for brick in state.bricks:
        if not brick.alive or not circle_hits_rect(ball, brick.x, brick.y, brick.right, brick.bottom):
            continue
        if ball.kind == "bomb":
            explode_bomb(state, ball)
            return False
        reflect_from_brick(ball, brick, previous_x, previous_y)
        hit_brick(state, brick)
        break

    return ball.y - ball.radius <= ARENA_BOTTOM


def update_powerups(state, seconds):
    remaining = []
    for powerup in state.powerups:
        powerup.y += powerup.vy * seconds
        caught = circle_hits_rect(
            powerup,
            state.paddle.left,
            state.paddle.y,
            state.paddle.right,
            state.paddle.y + state.paddle.height,
        )
        if caught:
            if powerup.kind == "bomb":
                spawn_mirrored_ball(state, "bomb")
            elif powerup.kind == "multiball":
                spawn_mirrored_ball(state, "normal")
        elif powerup.y - powerup.radius <= ARENA_BOTTOM:
            remaining.append(powerup)
    state.powerups = remaining


def update_explosions(state, seconds):
    for explosion in state.explosions:
        explosion.age += seconds
    state.explosions = [
        explosion
        for explosion in state.explosions
        if explosion.age < explosion.duration
    ]


def update_game(state, seconds, move=0.0, mouse_x=None):
    if state.phase in {"won", "game_over"}:
        update_explosions(state, seconds)
        return

    state.paddle.x = mouse_x if mouse_x is not None else state.paddle.x + clamp(move, -1, 1) * PADDLE_SPEED * seconds
    state.paddle.x = clamp(state.paddle.x, ARENA_LEFT + state.paddle.width / 2, ARENA_RIGHT - state.paddle.width / 2)

    if state.phase == "ready":
        for ball in state.balls:
            if ball.attached:
                ball.x = state.paddle.x
                ball.y = state.paddle.y - ball.radius - 2
        return
    if state.phase != "playing":
        return

    state.balls = [ball for ball in list(state.balls) if update_ball(state, ball, seconds)]
    update_powerups(state, seconds)
    update_explosions(state, seconds)

    if not any(brick.alive for brick in state.bricks):
        if state.level + 1 < len(LEVELS):
            state.level += 1
            state.bricks = make_bricks(state.level)
            state.lives = 3
            state.reset_ball()
        else:
            state.phase = "won"
        return

    if not state.balls:
        state.lives -= 1
        if state.lives <= 0:
            state.phase = "game_over"
            state.powerups = []
        else:
            state.reset_ball()
