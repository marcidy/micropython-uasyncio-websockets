"""
Websockets client for micropython

Directly based on
https://github.com/danni/uwebsockets

which is based very heavily off
https://github.com/aaugustin/websockets/blob/master/websockets/client.py

"""

import binascii as binascii
import random as random
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
from .protocol import Websocket, urlparse


class WebsocketClient(Websocket):
    is_client = True


async def connect(uri):
    """
    Connect a websocket.
    """

    uri = urlparse(uri)
    ss, _ = await asyncio.open_connection(uri.hostname, uri.port)

    if uri.proto == "wss":
        print(__file__ + ": importing ssl")
        import ssl
        print(__file__ + ": trying ssl")
        ssl_sock = ssl.wrap_socket(ss.s)
        ss.s = ssl_sock

    def send_header(header, *args):
        ss.write(header % args + b'\r\n')

    # Sec-WebSocket-Key is 16 bytes of random base64 encoded
    key = binascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]

    print("sending headers")
    send_header(b'GET %s HTTP/1.1', uri.path.encode('utf-8') or b'/')
    send_header(b'Host: %s:%d', uri.hostname.encode('utf-8'), uri.port)
    send_header(b'Connection: Upgrade')
    send_header(b'Upgrade: websocket')
    send_header(b'Sec-WebSocket-Key: %s', key)
    send_header(b'Sec-WebSocket-Version: 13')
    send_header(b'Origin: http://localhost')
    send_header(b'')

    await ss.drain()

    header = (await ss.readline())[:-2]
    if not header.startswith(b'HTTP/1.1 101 '):
        return False

    # We don't (currently) need these headers
    # FIXME: should we check the return key?

    while header:
        header = await ss.readline()
        print(header)
        if header == b"\r\n":
            break

    return WebsocketClient(ss)
