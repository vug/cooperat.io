import asyncio
import datetime
import functools
import json
import math
import random

import websockets


async def game_loop(game_state):
    """Update game state periodically.

    This happens independent of client connections, hence no websocket references are
    needed.
    """
    while True:
        ts_prev = game_state["ts"]
        ts_curr = datetime.datetime.utcnow().timestamp()
        delta_t = ts_curr - ts_prev

        update_positions(game_state, delta_t)

        game_state["ts"] = datetime.datetime.utcnow().timestamp()
        game_state["tick_no"] += 1
        await asyncio.sleep(0.025)


def update_positions(game_state, delta_t):
    for u in game_state["units"]:
        u["x"] = (u["x"] + math.cos(u["dir"]) * u["speed"] * delta_t) % 10
        u["y"] = (u["y"] + math.sin(u["dir"]) * u["speed"] * delta_t) % 10
        if u["type"] == "ghost":
            u["dir"] = (u["dir"] + random.random() * 0.4 - 0.2) % (2.0 * math.pi)


async def handler(ws, path, game_state):
    print(f"client connected: {ws.remote_address}")
    while True:
        await ws.send(json.dumps(game_state))
        await asyncio.sleep(0.025)


async def run_server():
    game_state = init_game_state()
    game_loop_routine = game_loop(game_state)
    # Add an argument to handler
    bound_handler = functools.partial(handler, game_state=game_state)
    ws_server_routine = websockets.serve(bound_handler, "localhost", 8765)
    await asyncio.gather(game_loop_routine, ws_server_routine)


def init_game_state():
    gs = {"units": [], "ts": datetime.datetime.utcnow().timestamp(), "tick_no": 0}
    n_units = 10
    for _ in range(n_units):
        u = {
            "type": "ghost",
            "x": random.random() * 10,
            "y": random.random() * 10,
            "speed": 1.0,
            "dir": random.random() * math.pi,
        }
        gs["units"].append(u)
    return gs


if __name__ == "__main__":
    asyncio.run(run_server())
