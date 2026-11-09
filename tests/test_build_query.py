"""Tests for the JSON-RPC parameters built by the library getters."""

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from pykodi import Kodi


def recording_kodi() -> "tuple[Kodi, List[Dict[str, Any]]]":
    calls: List[Dict[str, Any]] = []

    async def record(**params: Any) -> Dict[str, Any]:
        calls.append(params)
        return {}

    server = SimpleNamespace(
        AudioLibrary=SimpleNamespace(GetAlbums=record, GetSongs=record),
        VideoLibrary=SimpleNamespace(GetEpisodes=record),
    )
    return Kodi(SimpleNamespace(server=server)), calls


def test_get_episodes_sends_season_zero() -> None:
    kodi, calls = recording_kodi()

    asyncio.run(kodi.get_episodes(tv_show_id=1, season_id=0))

    assert calls == [{"tvshowid": 1, "season": 0}]


@pytest.mark.parametrize("method", ["get_albums", "get_songs"])
def test_unfiltered_library_query_omits_filter(method: str) -> None:
    kodi, calls = recording_kodi()

    asyncio.run(getattr(kodi, method)())

    assert calls == [{}]
