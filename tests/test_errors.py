"""Tests for the errors exported by pykodi."""

import asyncio
import json

import aiohttp
from aiohttp import web
import jsonrpc_base
import pytest

import pykodi
from pykodi import Kodi, get_kodi_connection


def test_errors_are_the_jsonrpc_base_errors() -> None:
    assert pykodi.ProtocolError is jsonrpc_base.ProtocolError
    assert pykodi.TransportError is jsonrpc_base.TransportError


def test_kodi_error_reply_raises_protocol_error() -> None:
    async def run() -> None:
        async def jsonrpc(request: web.Request) -> web.WebSocketResponse:
            websocket = web.WebSocketResponse()
            await websocket.prepare(request)
            async for message in websocket:
                call = json.loads(message.data)
                await websocket.send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": call["id"],
                        "error": {"code": -32601, "message": "Method not found."},
                    }
                )
            return websocket

        app = web.Application()
        app.router.add_get("/jsonrpc", jsonrpc)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "127.0.0.1", 0).start()
        port = runner.addresses[0][1]
        try:
            async with aiohttp.ClientSession() as session:
                connection = get_kodi_connection(
                    "127.0.0.1", 8080, port, None, None, timeout=5, session=session
                )
                await connection.connect()
                try:
                    with pytest.raises(pykodi.ProtocolError):
                        await Kodi(connection).get_application_properties(["version"])
                finally:
                    await connection.close()
        finally:
            await runner.cleanup()

    asyncio.run(run())


def test_request_without_connection_raises_transport_error() -> None:
    async def run() -> None:
        async with aiohttp.ClientSession() as session:
            connection = get_kodi_connection(
                "127.0.0.1", 8080, 9090, None, None, timeout=5, session=session
            )
            with pytest.raises(pykodi.TransportError):
                await Kodi(connection).get_application_properties(["version"])

    asyncio.run(run())
