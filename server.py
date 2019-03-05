import asyncio
import datetime
import functools
import json
import logging
import math
import random

import websockets


def game_loop(game_state):
    """Update game state periodically.

    This happens independent of client connections, hence no websocket references are
    needed.
    """
    ts_prev = game_state["ts"]
    ts_curr = datetime.datetime.utcnow().timestamp()
    delta_t = ts_curr - ts_prev

    update_positions(game_state, delta_t)

    game_state["ts"] = datetime.datetime.utcnow().timestamp()
    game_state["tick_no"] += 1


def update_positions(game_state, delta_t):
    for u in game_state["units"]:
        u["x"] = (u["x"] + math.cos(u["dir"]) * u["speed"] * delta_t) % 10
        u["y"] = (u["y"] + math.sin(u["dir"]) * u["speed"] * delta_t) % 10
        if u["type"] == "ghost":
            u["dir"] = (u["dir"] + random.random() * 0.4 - 0.2) % (2.0 * math.pi)


async def producer_handler(ws, path, game_state):
    while True:
        game_loop(game_state)
        await ws.send(json.dumps(game_state))
        await asyncio.sleep(0.025)


async def consumer_handler(ws, path, game_state):
    async for msg in ws:
        logging.info(f"{ws.remote_address}: {msg}")


async def connection_handler(ws, path, game_state):
    logging.info(f"client connected: {ws.remote_address}")
    u = {
        "type": "player",
        "x": random.random() * 10,
        "y": random.random() * 10,
        "speed": 1.0,
        "dir": 0,
    }
    game_state["units"].append(u)
    producer_task = asyncio.create_task(producer_handler(ws, path, game_state))
    consumer_task = asyncio.create_task(consumer_handler(ws, path, game_state))
    done, pending = await asyncio.wait(
        [producer_task, consumer_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()


def main():
    game_state = init_game_state()
    # Make ws_handler accept one more argument
    bound_handler = functools.partial(connection_handler, game_state=game_state)
    ws_server = websockets.serve(ws_handler=bound_handler, host="localhost", port=8765)
    asyncio.get_event_loop().run_until_complete(ws_server)
    asyncio.get_event_loop().run_forever()


def init_game_state():
    gs = {"units": [], "ts": datetime.datetime.utcnow().timestamp(), "tick_no": 0}
    n_ghosts = 10
    for _ in range(n_ghosts):
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
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    main()
