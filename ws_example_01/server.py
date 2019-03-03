import asyncio
import websockets


async def hello(websocket, path):
    name = await websocket.recv()
    print(f"< {name}")

    greeting = f"Hello {name}!"

    await websocket.send(greeting)
    print(f"> {greeting}")


if __name__ == "__main__":
    start_server = websockets.serve(hello, "localhost", 8765)

    # event_loop = asyncio.get_event_loop()
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
