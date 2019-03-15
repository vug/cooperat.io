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
        self.world_size = 30
        self.player_interaction_radius = 3.0
        self.sight_range = 6


def game_loop(game_state):
    """Update game state periodically.

    This happens independent of client connections, hence no websocket references are
    needed.
    """
    ts_prev = game_state.ts
    ts_curr = datetime.datetime.utcnow().timestamp()
    delta_t = ts_curr - ts_prev

    update_positions(game_state, delta_t)
    touched_players_ids = detect_collisions(game_state)
    touched_players = [game_state.units[ix] for ix in touched_players_ids]
    if touched_players_ids:
        logging.info(
            (
                f"tick: {game_state.tick_no}."
                f"touched by ghost: {[p['nickname'] for p in touched_players]}"
            )
        )
    for u in touched_players:
        u["type"] = "ghost"
        u["is_marked"] = False

    game_state.ts = datetime.datetime.utcnow().timestamp()
    game_state.tick_no += 1


def update_positions(game_state, delta_t):
    for id, u in game_state.units.items():
        u["x"] = (
            u["x"] + math.cos(u["dir"]) * u["speed"] * delta_t
        ) % game_state.world_size
        u["y"] = (
            u["y"] - math.sin(u["dir"]) * u["speed"] * delta_t
        ) % game_state.world_size
        if u["type"] == "ghost":
            u["dir"] = (u["dir"] + random.random() * 0.4 - 0.2) % (2.0 * math.pi)


def detect_collisions(game_state):
    """Get the list of players that are touched by a ghost."""
    player_units = [u for u in game_state.units.values() if u["type"] == "player"]
    ghost_units = [u for u in game_state.units.values() if u["type"] == "ghost"]
    touched_players = []
    for p in player_units:
        for g in ghost_units:
            if p["x"] - 1 < g["x"] < p["x"] + 1 and p["y"] - 1 < g["y"] < p["y"] + 1:
                touched_players.append(p)
    return [u["id"] for u in touched_players]


async def producer_handler(ws, path, game_state):
    try:
        while True:
            game_loop(game_state)
            message = {"ts": game_state.ts, "tick_no": game_state.tick_no}
            message["units"] = []
            client_uid = connectedSockets[ws]
            client_unit = game_state.units[client_uid]
            is_client_warrior = client_unit["class"] == "warrior"
            for uid, u in game_state.units.items():
                is_client = uid == client_uid
                is_ghost = u["type"] == "ghost"
                is_in_sight = (
                    abs(u["x"] - client_unit["x"]) < game_state.sight_range + 1.0
                    and abs(u["y"] - client_unit["y"]) < game_state.sight_range + 1.0
                )
                if not is_client and not is_in_sight:
                    continue
                if is_client_warrior and is_ghost and not u["is_marked"]:
                    continue
                d = {
                    k: u[k]
                    for k in ["type", "x", "y", "dir", "nickname", "class", "is_marked"]
                    if k in u
                }
                if u["type"] == "player" and is_client:
                    d["type"] = "me"
                message["units"].append(d)

            await ws.send(json.dumps(message))
            await asyncio.sleep(0.025)
    except websockets.ConnectionClosed:
        logging.info(f"User {ws.remote_address} has left.")
    finally:
        uid = connectedSockets[ws]
        client_unit = game_state.units[uid]
        if client_unit["type"] == "ghost":
            logging.info(f"Keeping {ws.remote_address}'s unit. id: {uid}")
        else:
            logging.info(f"Removing {ws.remote_address}'s unit. id: {uid}")
            game_state.units.pop(uid, None)
        connectedSockets.pop(ws, None)


async def consumer_handler(ws, path, game_state):
    async for msg_str in ws:
        logging.info(f"{ws.remote_address}: {msg_str}")
        msg = json.loads(msg_str)
        client_unit = game_state.units[connectedSockets[ws]]
        if client_unit["type"] == "ghost":
            continue
        msg_type = msg["type"]

        if msg_type == "command":
            command = msg["command"]
            if command == "up":
                client_unit["dir"] = math.pi / 2
                client_unit["speed"] = 1.5
            if command == "down":
                client_unit["dir"] = -math.pi / 2
                client_unit["speed"] = 1.5
            if command == "left":
                client_unit["dir"] = math.pi
                client_unit["speed"] = 1.5
            if command == "right":
                client_unit["dir"] = 0
                client_unit["speed"] = 1.5
            if command == "stop":
                client_unit["speed"] = 0.0
            if command == "mark":
                ghost_id, distance = get_target(game_state, client_unit)
                ghost = game_state.units.get(ghost_id, None)
                if ghost:
                    ghost["is_marked"] = True
            if command == "attack":
                ghost_id, distance = get_target(game_state, client_unit)
                if ghost_id is not None:
                    game_state.units.pop(ghost_id)


def get_target(game_state, client_unit):
    closest_ghost_id = None
    closest_distance = 1_000_000
    for uid, u in game_state.units.items():
        if u["type"] != "ghost":
            continue
        dist2 = math.pow(u["x"] - client_unit["x"], 2.0) + math.pow(
            u["y"] - client_unit["y"], 2.0
        )
        dist = math.sqrt(dist2)
        if dist < closest_distance:
            closest_distance = dist
            closest_ghost_id = uid
    if closest_distance > game_state.player_interaction_radius:
        return (None, None)
    return (closest_ghost_id, closest_distance)


async def connection_handler(ws, path, game_state):
    """Register producer and consumer tasks after initial handshake with the client."""
    is_connection_established = await handshake(ws, game_state)
    if not is_connection_established:
        return
    producer_task = asyncio.create_task(producer_handler(ws, path, game_state))
    consumer_task = asyncio.create_task(consumer_handler(ws, path, game_state))
    done, pending = await asyncio.wait(
        [producer_task, consumer_task], return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()


async def handshake(ws, game_state):
    """Initial synchronous handshake with the client.

    Wait for the nickname and unit class. Send essential information such as
    the size of the world.

    Return whether handshake was successful or not.
    """
    logging.info(f"client connected: {ws.remote_address}")
    msg_str = await ws.recv()
    msg = json.loads(msg_str)
    logging.info(f"{ws.remote_address}'s first message: {msg}")
    msg_type = msg["type"]
    if msg_type != "init":
        return False
    nickname = msg["nickname"]
    unit_class = msg["class"]

    msg = {
        "type": "init",
        "world_size": game_state.world_size,
        "interaction_radius": game_state.player_interaction_radius,
        "sight_range": game_state.sight_range,
    }
    await ws.send(json.dumps(msg))

    uid = game_state.num_units_created
    u = {
        "id": uid,
        "type": "player",
        "x": random.random() * game_state.world_size,
        "y": random.random() * game_state.world_size,
        "speed": 3.0,
        "dir": 0,
        "nickname": nickname,
        "class": unit_class,
    }
    connectedSockets[ws] = uid
    game_state.units[uid] = u
    game_state.num_units_created += 1
    logging.info(f"Client is given id {uid} and added to game.")
    return True


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
        uid = gs.num_units_created
        unit = {
            "id": uid,
            "type": "ghost",
            "x": random.random() * gs.world_size,
            "y": random.random() * gs.world_size,
            "speed": 1.5,
            "dir": random.random() * math.pi,
            "is_marked": False,
        }
        gs.units[uid] = unit
        gs.num_units_created += 1
    return gs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    main()
