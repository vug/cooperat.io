import asyncio
import datetime
import json
import functools
import random

import websockets


async def game_loop(game_state):
    while True:
        # update game state
        for u in game_state["units"]:
            u["x"] = (u["x"] + 0.05 * random.random() - 0.025) % 10
            u["y"] = (u["y"] + 0.05 * random.random() - 0.025) % 10
        game_state["ts"] = datetime.datetime.utcnow().isoformat()
        await asyncio.sleep(0.025)


async def serve(ws, path, game_state):
    print(f"client connected: {ws.remote_address}")
    while True:
        await ws.send(json.dumps(game_state))
        await asyncio.sleep(0.025)


async def run_all():
    gs = {"units": [], "ts": None}
    n_units = 10
    for _ in range(n_units):
        u = {"x": random.random() * 10, "y": random.random() * 10}
        gs["units"].append(u)

    start_server = websockets.serve(
        functools.partial(serve, game_state=gs), "localhost", 8765
    )
    await asyncio.gather(game_loop(gs), start_server)


if __name__ == "__main__":

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run_all())
    event_loop.run_forever()
