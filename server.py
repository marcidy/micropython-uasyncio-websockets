import binascii
import hashlib
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio
import re
from .protocol import Websocket


class WebsocketServer(Websocket):
    is_client = False


REQ_RE = re.compile(
    br'^(([^:/\\?#]+):)?' +  # scheme                # NOQA
    br'(//([^/\\?#]*))?' +   # user:pass@hostport    # NOQA
    br'([^\\?#]*)' +         # route                 # NOQA
    br'(\\?([^#]*))?' +      # query                 # NOQA
    br'(#(.*))?')            # fragment              # NOQA


def make_respkey(webkey):
    d = hashlib.sha1(webkey)
    d.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
    respkey = d.digest()
    return binascii.b2a_base64(respkey).strip()


async def connect(reader, writer, cb):
    print("in connect")
    webkey = None

    request = await reader.readline()

    try:
        method, uri, proto = request.split(b" ")
    except Exception as e:
        print("Malformed request: {}".format(request))
        print(e)
        return

    m = re.match(REQ_RE, uri)
    path = m.group(5) if m else "/"

    while True:
        header = await reader.readline()
        if header == b'' or header == b'\r\n':
            break

        print(header)
        if header.startswith(b'Sec-WebSocket-Key:'):
            webkey = header.split(b":", 1)[1]
            webkey = webkey.strip()

    if not webkey:
        writer.close()
        await writer.wait_closed()
        return

    respkey = make_respkey(webkey)

    print("responding")
    writer.write(b"HTTP/1.1 101 Switching Protocols\r\n")
    writer.write(b"Upgrade: websocket\r\n")
    writer.write(b"Connection: Upgrade\r\n")
    writer.write(b"Sec-WebSocket-Accept: " + respkey + b"\r\n")
    writer.write(b"Server: Micropython\r\n")
    writer.write(b"\r\n")
    await writer.drain()

    ws = WebsocketServer(writer)
    asyncio.create_task(cb(ws, path))


async def serve(cb, host, port):

    async def _connect(reader, writer):
        await connect(reader, writer, cb)

    return await asyncio.start_server(_connect, host, port)
