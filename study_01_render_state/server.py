import asyncio
import datetime
import functools
import random

import websockets


class Unit(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y


async def game_loop(game_state):
    while True:
        # update game state
        print(datetime.datetime.utcnow().isoformat(), game_state)
        await asyncio.sleep(0.5)


async def serve(ws, path, game_state):
    print(f"game state: {game_state}")
    while True:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        await ws.send(now)
        await asyncio.sleep(random.random() * 3)


async def all_routines():
    gs = {"units": []}

    start_server = websockets.serve(
        functools.partial(serve, game_state=gs), "localhost", 8765
    )
    await asyncio.gather(game_loop(gs), start_server)


if __name__ == "__main__":

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(all_routines())
    event_loop.run_forever()
