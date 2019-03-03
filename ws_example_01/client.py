import asyncio
import websockets


async def hello():
    async with websockets.connect('ws://localhost:8765') as ws:
        name = input("What's your name? ")

        await ws.send(name)
        print(f"> {name}")

        greeting = await ws.recv()
        print(f"< {greeting}")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(hello())
