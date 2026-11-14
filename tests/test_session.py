"""Tests for the aiohttp session of a connection."""

import asyncio
from typing import Any, List

import aiohttp
from aiohttp import web
import pytest

from pykodi import Kodi, get_kodi_connection


@pytest.fixture
def created_sessions(monkeypatch: pytest.MonkeyPatch) -> List[aiohttp.ClientSession]:
    """Record every aiohttp session that is created."""
    sessions: List[aiohttp.ClientSession] = []
    client_session = aiohttp.ClientSession

    def create(*args: Any, **kwargs: Any) -> aiohttp.ClientSession:
        session = client_session(*args, **kwargs)
        sessions.append(session)
        return session

    monkeypatch.setattr(aiohttp, "ClientSession", create)
    return sessions


async def start_kodi() -> web.AppRunner:
    """Start a websocket server that answers every request with "pong"."""

    async def jsonrpc(request: web.Request) -> web.WebSocketResponse:
        websocket = web.WebSocketResponse()
        await websocket.prepare(request)
        async for message in websocket:
            request_id = message.json()["id"]
            await websocket.send_json(
                {"jsonrpc": "2.0", "id": request_id, "result": "pong"}
            )
        return websocket

    app = web.Application()
    app.router.add_get("/jsonrpc", jsonrpc)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 0).start()
    return runner


def test_ws_connect_after_close(
    created_sessions: List[aiohttp.ClientSession],
) -> None:
    async def run() -> None:
        runner = await start_kodi()
        port = runner.addresses[0][1]
        try:
            connection = get_kodi_connection(
                "127.0.0.1", 8080, port, None, None, timeout=5
            )
            kodi = Kodi(connection)
            await asyncio.wait_for(connection.connect(), 5)
            assert await kodi.ping()
            await asyncio.wait_for(connection.close(), 5)
            await asyncio.wait_for(connection.connect(), 5)
            assert await kodi.ping()
            await asyncio.wait_for(connection.close(), 5)
        finally:
            await runner.cleanup()

    asyncio.run(run())
    assert created_sessions
    assert all(session.closed for session in created_sessions)


def test_http_close_closes_the_session(
    created_sessions: List[aiohttp.ClientSession],
) -> None:
    async def run() -> None:
        connection = get_kodi_connection("127.0.0.1", 8080, None, None, None)
        await connection.close()

    asyncio.run(run())
    assert len(created_sessions) == 1
    assert created_sessions[0].closed


@pytest.mark.parametrize("websocket", [False, True])
def test_close_leaves_a_passed_session_open(websocket: bool) -> None:
    async def run() -> None:
        runner = await start_kodi()
        port = runner.addresses[0][1]
        try:
            async with aiohttp.ClientSession() as session:
                connection = get_kodi_connection(
                    "127.0.0.1",
                    port,
                    port if websocket else None,
                    None,
                    None,
                    timeout=5,
                    session=session,
                )
                await asyncio.wait_for(connection.connect(), 5)
                await asyncio.wait_for(connection.close(), 5)
                assert not session.closed
        finally:
            await runner.cleanup()

    asyncio.run(run())
