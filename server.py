import asyncio
import datetime
import functools
import json
import logging
import math
import random

import websockets

connectedSockets = {}


class GameState(object):
    def __init__(self):
        self.units = {}
        self.ts = datetime.datetime.utcnow().timestamp()
        self.tick_no = 0
        self.num_units_created = 0


def game_loop(game_state):
    """Update game state periodically.

    This happens independent of client connections, hence no websocket references are
    needed.
    """
    ts_prev = game_state.ts
    ts_curr = datetime.datetime.utcnow().timestamp()
    delta_t = ts_curr - ts_prev

    update_positions(game_state, delta_t)

    game_state.ts = datetime.datetime.utcnow().timestamp()
    game_state.tick_no += 1


def update_positions(game_state, delta_t):
    for id, u in game_state.units.items():
        u["x"] = (u["x"] + math.cos(u["dir"]) * u["speed"] * delta_t) % 10
        u["y"] = (u["y"] - math.sin(u["dir"]) * u["speed"] * delta_t) % 10
        if u["type"] == "ghost":
            u["dir"] = (u["dir"] + random.random() * 0.4 - 0.2) % (2.0 * math.pi)


async def producer_handler(ws, path, game_state):
    try:
        while True:
            game_loop(game_state)
            message = {"ts": game_state.ts, "tick_no": game_state.tick_no}
            message["units"] = []
            for uid, u in game_state.units.items():
                d = {k: u[k] for k in ["type", "x", "y", "dir"]}
                if u["type"] == "player" and not u["active"]:
                    continue
                if u["type"] == "player" and u["active"]:
                    d.update({k: u[k] for k in ["nickname", "class"]})
                is_clients_unit = uid == connectedSockets[ws]
                if is_clients_unit:
                    d["type"] = "me"
                message["units"].append(d)

            await ws.send(json.dumps(message))
            await asyncio.sleep(0.025)
    except websockets.ConnectionClosed:
        logging.info(f"User {ws.remote_address} has left.")
    finally:
        uid = connectedSockets[ws]
        logging.info(f"Removing {ws.remote_address}'s unit. id: {uid}")
        game_state.units.pop(uid, None)
        connectedSockets.pop(ws, None)


async def consumer_handler(ws, path, game_state):
    async for msg_str in ws:
        logging.info(f"{ws.remote_address}: {msg_str}")
        msg = json.loads(msg_str)
        unit = game_state.units[connectedSockets[ws]]
        msg_type = msg["type"]

        if msg_type == "init":
            nickname = msg["nickname"]
            unit_class = msg["class"]
            unit["nickname"] = nickname
            unit["class"] = unit_class
            unit["active"] = True
            # await ws.send(json.dumps)

        if msg_type == "command":
            command = msg["command"]
            if command == "up":
                unit["dir"] = math.pi / 2
            if command == "down":
                unit["dir"] = -math.pi / 2
            if command == "left":
                unit["dir"] = math.pi
            if command == "right":
                unit["dir"] = 0


async def connection_handler(ws, path, game_state):
    uid = game_state.num_units_created
    u = {
        "type": "player",
        "x": random.random() * 10,
        "y": random.random() * 10,
        "speed": 1.0,
        "dir": 0,
        "active": False,
    }
    logging.info(f"client connected: {ws.remote_address}. Given id: {uid}.")
    connectedSockets[ws] = uid
    game_state.units[uid] = u
    game_state.num_units_created += 1
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
    gs = GameState()
    n_ghosts = 10
    for _ in range(n_ghosts):
        unit = {
            "type": "ghost",
            "x": random.random() * 10,
            "y": random.random() * 10,
            "speed": 1.0,
            "dir": random.random() * math.pi,
        }
        uid = gs.num_units_created
        gs.units[uid] = unit
        gs.num_units_created += 1
    return gs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    main()
