import asyncio
import datetime
import functools
import json
import math
import random

import websockets


async def game_loop(game_state):
    while True:
        ts_prev = game_state["ts"]
        ts_curr = datetime.datetime.utcnow().timestamp()
        delta_t = ts_curr - ts_prev
        for u in game_state["units"]:
            u["x"] = (u["x"] + math.cos(u["dir"]) * u["speed"] * delta_t) % 10
            u["y"] = (u["y"] + math.sin(u["dir"]) * u["speed"] * delta_t) % 10
            u["dir"] = (u["dir"] + random.random() * 0.4 - 0.2) % (2.0 * math.pi)
        game_state["ts"] = datetime.datetime.utcnow().timestamp()
        game_state["tick_no"] += 1
        await asyncio.sleep(0.025)


async def serve(ws, path, game_state):
    print(f"client connected: {ws.remote_address}")
    while True:
        await ws.send(json.dumps(game_state))
        await asyncio.sleep(0.025)


async def run_all():
    game_state = init_game_state()
    game_loop_routine = game_loop(game_state)
    ws_server_routine = websockets.serve(
        functools.partial(serve, game_state=game_state), "localhost", 8765
    )
    await asyncio.gather(game_loop_routine, ws_server_routine)


def init_game_state():
    gs = {"units": [], "ts": datetime.datetime.utcnow().timestamp(), "tick_no": 0}
    n_units = 10
    for _ in range(n_units):
        u = {
            "x": random.random() * 10,
            "y": random.random() * 10,
            "speed": 1.0,
            "dir": random.random() * math.pi,
        }
        gs["units"].append(u)
    return gs


if __name__ == "__main__":
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run_all())
    event_loop.run_forever()
