"""Testable physics model for the brick breaker.

The Ball class and fixed-step structure are adapted from SD5913 Week 7.
Rendering stays in main.py so this module can be tested without Pygame.
"""

from dataclasses import dataclass, field
import math

WIDTH, HEIGHT = 960, 640
ARENA_LEFT, ARENA_RIGHT = 72.0, WIDTH - 72.0
ARENA_TOP, ARENA_BOTTOM = 96.0, HEIGHT - 54.0
PADDLE_WIDTH, PADDLE_HEIGHT = 132.0, 15.0
PADDLE_Y, PADDLE_SPEED = ARENA_BOTTOM - 33.0, 560.0
BALL_RADIUS, BALL_SPEED = 9.0, 390.0
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
    ball: Ball = field(default_factory=lambda: Ball(WIDTH / 2, PADDLE_Y - BALL_RADIUS - 2, 0, 0))
    level: int = 0
    bricks: list[Brick] = field(default_factory=list)
    score: int = 0
    lives: int = 3
    phase: str = "ready"

    def __post_init__(self):
        if not self.bricks:
            self.bricks = make_bricks(self.level)

    def reset_ball(self):
        self.paddle.x = WIDTH / 2
        self.ball = Ball(self.paddle.x, self.paddle.y - BALL_RADIUS - 2, 0, 0)
        self.phase = "ready"

    def restart(self):
        self.level = 0
        self.paddle = Paddle(WIDTH / 2)
        self.bricks = make_bricks(self.level)
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


def circle_hits_rect(ball, left, top, right, bottom):
    dx = ball.x - clamp(ball.x, left, right)
    dy = ball.y - clamp(ball.y, top, bottom)
    return dx * dx + dy * dy <= ball.radius * ball.radius


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


def bounce_from_paddle(state, previous_y):
    ball, paddle = state.ball, state.paddle
    if ball.vy <= 0 or previous_y + ball.radius > paddle.y + 4:
        return
    if not circle_hits_rect(ball, paddle.left, paddle.y, paddle.right, paddle.y + paddle.height):
        return
    ball.y = paddle.y - ball.radius
    offset = clamp((ball.x - paddle.x) / (paddle.width / 2), -1.0, 1.0)
    ball.vx = BALL_SPEED * offset * 0.88
    ball.vy = -math.sqrt(max(1.0, BALL_SPEED**2 - ball.vx**2))


def update_game(state, seconds, move=0.0, mouse_x=None):
    if state.phase in {"won", "game_over"}:
        return
    state.paddle.x = mouse_x if mouse_x is not None else state.paddle.x + clamp(move, -1, 1) * PADDLE_SPEED * seconds
    state.paddle.x = clamp(state.paddle.x, ARENA_LEFT + state.paddle.width / 2, ARENA_RIGHT - state.paddle.width / 2)
    if state.ball.attached:
        state.ball.x = state.paddle.x
        state.ball.y = state.paddle.y - state.ball.radius - 2
        return
    if state.phase != "playing":
        return

    ball = state.ball
    previous_x, previous_y = ball.x, ball.y
    ball.x += ball.vx * seconds
    ball.y += ball.vy * seconds
    if ball.x - ball.radius < ARENA_LEFT:
        ball.x, ball.vx = ARENA_LEFT + ball.radius, abs(ball.vx)
    elif ball.x + ball.radius > ARENA_RIGHT:
        ball.x, ball.vx = ARENA_RIGHT - ball.radius, -abs(ball.vx)
    if ball.y - ball.radius < ARENA_TOP:
        ball.y, ball.vy = ARENA_TOP + ball.radius, abs(ball.vy)

    bounce_from_paddle(state, previous_y)
    for brick in state.bricks:
        if brick.alive and circle_hits_rect(ball, brick.x, brick.y, brick.right, brick.bottom):
            reflect_from_brick(ball, brick, previous_x, previous_y)
            brick.hits_left -= 1
            if brick.hits_left <= 0:
                brick.alive = False
                state.score += 100
            break
    if not any(brick.alive for brick in state.bricks):
        if state.level + 1 < len(LEVELS):
            state.level += 1
            state.bricks = make_bricks(state.level)
            state.lives = 3
            state.reset_ball()
        else:
            state.phase = "won"
    elif ball.y - ball.radius > ARENA_BOTTOM:
        state.lives -= 1
        if state.lives <= 0:
            state.phase = "game_over"
            ball.attached = True
            ball.vx = ball.vy = 0
        else:
            state.reset_ball()
