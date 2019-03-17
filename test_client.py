import argparse
import asyncio
import json
import random

import websockets


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Create a cooperat.io bot. "
            "Connect to server. "
            "Handshake. "
            "Commit random actions."
        )
    )
    parser.add_argument(
        "--unit-class",
        "-c",
        help="Class of client unit.",
        choices=["warrior", "psychic"],
        required=True,
    )
    parser.add_argument(
        "--nickname", "-n", help="Nickname of client unit.", required=True
    )
    args = parser.parse_args()
    return args


async def handshake(cls, nickname):
    async with websockets.connect("ws://localhost:8765") as ws:
        msg = {"type": "init", "class": cls, "nickname": nickname}
        await ws.send(json.dumps(msg))

        msg_str = await ws.recv()
        msg = json.loads(msg_str)

        producer_task = asyncio.create_task(producer_handler(ws, cls))
        consumer_task = asyncio.create_task(consumer_handler(ws))
        done, pending = await asyncio.wait(
            [producer_task, consumer_task], return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()


async def producer_handler(ws, cls):
    action = {"warrior": "attack", "psychic": "mark"}
    commands = ["up", "down", "left", "right", action]
    try:
        while True:
            cmd = random.choice(commands)
            msg = {"type": "command", "command": cmd}
            await ws.send(json.dumps(msg))
            await asyncio.sleep(0.5)
    except websockets.ConnectionClosed:
        print("server disconnected.")


async def consumer_handler(ws):
    async for msg_str in ws:
        msg = json.loads(msg_str)
        is_alive = any([u["type"] == "me" for u in msg["game"]["units"]])
        if not is_alive:
            return


def main():
    args = parse_arguments()
    asyncio.get_event_loop().run_until_complete(
        handshake(args.unit_class, args.nickname)
    )


if __name__ == "__main__":
    main()
