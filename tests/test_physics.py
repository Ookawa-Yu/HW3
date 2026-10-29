import math

from physics import ARENA_LEFT, BALL_RADIUS, LEVELS, GameState, update_game


def aim_ball_at_brick(state, brick):
    state.phase = "playing"
    state.ball.attached = False
    state.ball.x = brick.x + brick.width / 2
    state.ball.y = brick.y - BALL_RADIUS - 0.1
    state.ball.vx, state.ball.vy = 0, 240


def test_ball_reflects_from_left_wall():
    state = GameState()
    state.phase = "playing"
    state.ball.attached = False
    state.ball.x = ARENA_LEFT + BALL_RADIUS + 0.2
    state.ball.y = 400
    state.ball.vx, state.ball.vy = -300, -40
    update_game(state, 1 / 60)
    assert state.ball.x >= ARENA_LEFT + BALL_RADIUS
    assert state.ball.vx > 0


def test_paddle_contact_sends_ball_upward():
    state = GameState()
    state.phase = "playing"
    state.ball.attached = False
    state.ball.x = state.paddle.x + 30
    state.ball.y = state.paddle.y - BALL_RADIUS - 1
    state.ball.vx, state.ball.vy = 0, 300
    update_game(state, 1 / 120)
    assert state.ball.vy < 0
    assert state.ball.vx > 0


def test_brick_disappears_and_awards_points():
    state = GameState()
    brick = state.bricks[0]
    aim_ball_at_brick(state, brick)
    update_game(state, 1 / 120)
    assert not brick.alive
    assert state.score == 100
    assert state.ball.vy < 0


def test_missing_ball_costs_a_life():
    state = GameState()
    state.phase = "playing"
    state.ball.attached = False
    state.ball.y, state.ball.vy = 700, 300
    update_game(state, 1 / 120)
    assert (state.lives, state.phase, state.ball.attached) == (2, "ready", True)


def test_first_level_has_32_one_hit_bricks():
    state = GameState()
    assert len(state.bricks) == 32
    assert all(brick.hits_left == 1 for brick in state.bricks)


def test_second_level_is_a_48_brick_board_with_two_hit_heart():
    state = GameState(level=1)
    assert len(state.bricks) == 48
    assert any(brick.hits_left == 2 for brick in state.bricks)
    assert any(brick.hits_left == 1 for brick in state.bricks)
    assert sum(brick.hits_left == 2 for brick in state.bricks) == 16


def test_two_hit_brick_changes_to_one_hit_before_disappearing():
    state = GameState(level=1)
    brick = next(brick for brick in state.bricks if brick.hits_left == 2)
    aim_ball_at_brick(state, brick)
    update_game(state, 1 / 120)
    assert brick.alive
    assert brick.hits_left == 1
    assert state.score == 0

    aim_ball_at_brick(state, brick)
    update_game(state, 1 / 120)
    assert not brick.alive
    assert state.score == 100


def test_clearing_first_level_loads_second_level():
    state = GameState()
    for brick in state.bricks:
        brick.alive = False
    final = state.bricks[-1]
    final.alive = True
    state.lives = 1
    aim_ball_at_brick(state, final)
    update_game(state, 1 / 120)
    assert state.level == 1
    assert state.lives == 3
    assert state.phase == "ready"
    assert len(state.bricks) == 48


def test_final_brick_of_second_level_completes_game():
    state = GameState(level=len(LEVELS) - 1)
    for brick in state.bricks:
        brick.alive = False
    final = state.bricks[-1]
    final.alive = True
    aim_ball_at_brick(state, final)
    update_game(state, 1 / 120)
    assert state.phase == "won"
    assert state.score == 100


def test_launch_speed_is_stable():
    state = GameState()
    state.launch()
    assert state.phase == "playing"
    assert not state.ball.attached
    assert math.hypot(state.ball.vx, state.ball.vy) == 390
