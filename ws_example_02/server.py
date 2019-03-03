import asyncio
import datetime
import random

import websockets


async def time(ws, path):
    while True:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        await ws.send(now)
        await asyncio.sleep(random.random() * 3)


if __name__ == "__main__":
    start_server = websockets.serve(time, "localhost", 8765)

    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(start_server)
    event_loop.run_forever()
