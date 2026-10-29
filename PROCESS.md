# Process

## Starting idea

I wanted to turn the Week 7 bouncing-ball example into a small desktop game.
The player moves a paddle to keep the ball in play. The program responds by
changing the ball direction, removing bricks, increasing the score and reducing
lives after a miss.

## First implementation

The first version used one level and only geometric shapes. The current version
adds a second level and hit-point-based bricks. I
separated physics.py from main.py so collisions can be tested without a window.
I retained the course Ball class idea and fixed-step update, removed gravity,
then added a paddle, bricks, lives, score and game states.

## Design decision

The Pygame window uses a white background and simple geometric shapes. White bricks take one hit, while pink bricks take two hits and turn white after
the first hit. The second level uses the pink bricks to form a heart outline.
The ball keeps
the Week 7 orange colour so the source transformation remains visible.

## Error or interruption handled

A missed ball removes one life, returns a new ball to the paddle and displays
the launch instruction. After the last life, the game shows an R restart
instruction. P/Escape lets the player pause and resume safely.

## User trial

Complete this after another person tries the desktop version:

- Date:
- What I asked the person to do:
- What they tried first:
- Where they hesitated or made a mistake:
- What feedback they understood or missed:
- Change I made after observing them:
- Why I made that change (or why I kept the design):

## AI use

OpenAI Codex helped inspect the Week 7 example, plan the desktop build, write
the initial Python implementation, add collision tests and draft documentation.
I reviewed and tested the generated work before submission.

- Suggestion kept: separate pure physics from Pygame rendering for testing.
- Suggestion changed or rejected: add one example after your own review.

## Next iteration

After the user trial, make one small change, run the tests and record it above.
