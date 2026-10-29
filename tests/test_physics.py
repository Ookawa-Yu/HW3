import math
from unittest.mock import patch

from physics import (
    ARENA_LEFT,
    BALL_RADIUS,
    BALL_SPEED,
    HEIGHT,
    LEVELS,
    PADDLE_Y,
    POWERUP_SPEED,
    Ball,
    Brick,
    GameState,
    PowerUp,
    should_drop_powerup,
    update_game,
)


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


def test_destroyed_brick_spawns_powerup_and_awards_points():
    state = GameState()
    brick = state.bricks[0]
    aim_ball_at_brick(state, brick)
    with patch("physics.random.random", return_value=0.05):
        update_game(state, 1 / 120)
    assert not brick.alive
    assert state.score == 100
    assert state.ball.vy < 0
    assert len(state.powerups) == 1
    assert state.powerups[0].kind == "multiball"
    assert state.missed_bomb_drops == 0
    assert state.powerups[0].x == brick.x + brick.width / 2
    assert state.powerups[0].y > brick.y + brick.height / 2


def test_missing_only_ball_costs_a_life():
    state = GameState()
    state.phase = "playing"
    state.ball.attached = False
    state.ball.y, state.ball.vy = HEIGHT + 50, 300
    update_game(state, 1 / 120)
    assert (state.lives, state.phase) == (2, "ready")
    assert len(state.balls) == 1
    assert state.ball.attached


def test_missing_one_of_multiple_balls_does_not_cost_a_life():
    state = GameState()
    state.launch()
    state.balls.append(Ball(300, HEIGHT + 50, 0, 300, attached=False))
    update_game(state, 1 / 120)
    assert state.lives == 3
    assert state.phase == "playing"
    assert len(state.balls) == 1


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


def test_two_hit_brick_drops_powerup_only_when_destroyed():
    state = GameState(level=1)
    brick = next(brick for brick in state.bricks if brick.hits_left == 2)
    aim_ball_at_brick(state, brick)
    update_game(state, 1 / 120)
    assert brick.alive
    assert brick.hits_left == 1
    assert state.score == 0
    assert not state.powerups

    aim_ball_at_brick(state, brick)
    with patch("physics.random.random", return_value=0.05):
        update_game(state, 1 / 120)
    assert not brick.alive
    assert state.score == 100
    assert {powerup.kind for powerup in state.powerups} == {"multiball", "bomb"}


def test_destroyed_brick_can_miss_random_drop():
    state = GameState()
    brick = state.bricks[0]
    aim_ball_at_brick(state, brick)
    with patch("physics.random.random", return_value=0.90):
        update_game(state, 1 / 120)
    assert not brick.alive
    assert not state.powerups
    assert state.missed_powerup_drops == 1


def test_eleventh_destroyed_brick_is_guaranteed_after_ten_misses():
    state = GameState()
    with patch("physics.random.random", return_value=0.90):
        results = [should_drop_powerup(state) for _ in range(11)]
    assert results == [False] * 10 + [True]
    assert state.missed_powerup_drops == 0


def test_random_drop_resets_pity_counter():
    state = GameState()
    state.missed_powerup_drops = 7
    with patch("physics.random.random", return_value=0.05):
        assert should_drop_powerup(state)
    assert state.missed_powerup_drops == 0


def test_bomb_item_has_independent_ten_miss_guarantee():
    state = GameState(level=1)
    with patch("physics.random.random", return_value=0.90):
        results = [should_drop_powerup(state, "bomb") for _ in range(11)]
    assert results == [False] * 10 + [True]
    assert state.missed_bomb_drops == 0


def test_powerup_falls_at_ball_speed():
    state = GameState()
    state.launch()
    state.ball.x, state.ball.y = 400, 420
    state.ball.vx, state.ball.vy = 0, -BALL_SPEED
    state.powerups = [PowerUp(200, 300)]
    update_game(state, 0.1)
    assert state.powerups[0].y == 300 + POWERUP_SPEED * 0.1
    assert POWERUP_SPEED == BALL_SPEED


def test_collecting_plus_powerup_adds_normal_mirrored_ball():
    state = GameState()
    state.launch()
    source = state.ball
    source.x, source.y = 400, 420
    source.vx, source.vy = 120, -math.sqrt(BALL_SPEED**2 - 120**2)
    state.powerups = [PowerUp(state.paddle.x, state.paddle.y - 1, "multiball")]
    update_game(state, 1 / 120)

    assert not state.powerups
    assert len(state.balls) == 2
    new_ball = state.balls[1]
    assert (new_ball.x, new_ball.y) == (source.x, source.y)
    assert new_ball.vx == -source.vx
    assert new_ball.vy == source.vy
    assert not new_ball.attached
    assert new_ball.kind == "normal"


def test_collecting_powerup_adds_mirrored_bomb_ball():
    state = GameState()
    state.launch()
    source = state.ball
    source.x, source.y = 400, 420
    source.vx, source.vy = 120, -math.sqrt(BALL_SPEED**2 - 120**2)
    state.powerups = [PowerUp(state.paddle.x, state.paddle.y - 1, "bomb")]
    update_game(state, 1 / 120)

    assert not state.powerups
    assert len(state.balls) == 2
    new_ball = state.balls[1]
    assert (new_ball.x, new_ball.y) == (source.x, source.y)
    assert new_ball.vx == -source.vx
    assert new_ball.vy == source.vy
    assert not new_ball.attached
    assert new_ball.kind == "bomb"


def test_taller_level_leaves_more_than_300_pixels_below_bricks():
    state = GameState(level=1)
    lowest_brick = max(brick.bottom for brick in state.bricks)
    assert HEIGHT == 760
    assert PADDLE_Y - lowest_brick > 300


def test_bomb_explodes_and_hits_nearby_bricks_once():
    target = Brick(300, 200, 80, 27, 0, 0, 1, 1)
    nearby = Brick(390, 200, 80, 27, 0, 1, 2, 2)
    far_away = Brick(600, 200, 80, 27, 0, 2, 1, 1)
    normal = Ball(700, 500, 100, -100, attached=False)
    bomb = Ball(340, 200 - BALL_RADIUS - 0.1, 0, 240, attached=False, kind="bomb")
    state = GameState(
        balls=[normal, bomb],
        bricks=[target, nearby, far_away],
        phase="playing",
    )

    with patch("physics.random.random", return_value=0.90):
        update_game(state, 1 / 120)

    assert not target.alive
    assert nearby.alive and nearby.hits_left == 1
    assert far_away.alive and far_away.hits_left == 1
    assert state.score == 100
    assert state.balls == [normal]
    assert len(state.explosions) == 1


def test_explosion_effect_expires():
    target = Brick(300, 200, 80, 27, 0, 0, 1, 1)
    survivor = Brick(600, 200, 80, 27, 0, 1, 1, 1)
    normal = Ball(700, 500, 100, -100, attached=False)
    bomb = Ball(340, 200 - BALL_RADIUS - 0.1, 0, 240, attached=False, kind="bomb")
    state = GameState(balls=[normal, bomb], bricks=[target, survivor], phase="playing")
    with patch("physics.random.random", return_value=0.90):
        update_game(state, 1 / 120)
    assert state.explosions
    update_game(state, 0.5)
    assert not state.explosions


def test_clearing_first_level_loads_second_level_and_restores_lives():
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
    assert not state.powerups


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
    assert math.hypot(state.ball.vx, state.ball.vy) == BALL_SPEED
