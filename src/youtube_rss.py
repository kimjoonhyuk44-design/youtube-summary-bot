from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import json
import re
from typing import Any
from urllib.request import Request, urlopen

import feedparser


@dataclass(frozen=True)
class Video:
    channel_id: str
    channel_name: str
    video_id: str
    title: str
    url: str
    published_at: str


def fetch_latest_videos(channel: dict[str, str], limit: int = 5) -> list[Video]:
    channel_id = channel["channel_id"]
    channel_name = channel["name"]
    feed = _parse_first_available_feed(channel_id)
    if feed is None:
        return _fetch_videos_from_channel_page(channel, limit)

    videos: list[Video] = []
    for entry in feed.entries[:limit]:
        video_id = _entry_video_id(entry)
        videos.append(
            Video(
                channel_id=channel_id,
                channel_name=channel_name,
                video_id=video_id,
                title=entry.get("title", "(no title)"),
                url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                published_at=_entry_published_at(entry),
            )
        )
    return videos


def _parse_first_available_feed(channel_id: str):
    upload_playlist_id = f"UU{channel_id[2:]}"
    feed_urls = [
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
        f"https://www.youtube.com/feeds/videos.xml?playlist_id={upload_playlist_id}",
    ]

    failures = []
    for feed_url in feed_urls:
        feed = feedparser.parse(feed_url)
        status = getattr(feed, "status", None)
        has_entries = bool(feed.entries)
        if has_entries and (status is None or status < 400):
            return feed

        exception = getattr(feed, "bozo_exception", None)
        failures.append(f"{feed_url} status={status} exception={exception!r}")

    print("RSS unavailable. Falling back to channel videos page.")
    for failure in failures:
        print(f"- {failure}")
    return None


def _fetch_videos_from_channel_page(channel: dict[str, str], limit: int) -> list[Video]:
    channel_id = channel["channel_id"]
    channel_name = channel["name"]
    base_url = channel.get("url", f"https://www.youtube.com/channel/{channel_id}")
    url = base_url.rstrip("/") + "/videos"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=30) as response:
        page = response.read().decode("utf-8", errors="replace")

    initial_data = _extract_yt_initial_data(page)
    videos: list[Video] = []
    seen_video_ids: set[str] = set()

    for video_id, title in _walk_video_items(initial_data):
        if not video_id or video_id in seen_video_ids:
            continue

        if not title:
            continue

        videos.append(
            Video(
                channel_id=channel_id,
                channel_name=channel_name,
                video_id=video_id,
                title=title,
                url=f"https://www.youtube.com/watch?v={video_id}",
                published_at="",
            )
        )
        seen_video_ids.add(video_id)

        if len(videos) >= limit:
            return videos

    if not videos:
        raise RuntimeError(f"Could not find videos on YouTube channel page: {url}")
    return videos


def _extract_yt_initial_data(page: str) -> Any:
    match = re.search(r"var ytInitialData = (\{.*?\});</script>", page)
    if not match:
        match = re.search(r"window\['ytInitialData'\] = (\{.*?\});", page)
    if not match:
        raise RuntimeError("Could not find ytInitialData in YouTube page")
    return json.loads(match.group(1))


def _walk_video_renderers(value: Any):
    if isinstance(value, dict):
        renderer = value.get("videoRenderer")
        if isinstance(renderer, dict):
            yield renderer
        for child in value.values():
            yield from _walk_video_renderers(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_video_renderers(child)


def _walk_video_items(value: Any):
    for renderer in _walk_video_renderers(value):
        yield renderer.get("videoId"), _renderer_title(renderer)

    for lockup in _walk_lockup_view_models(value):
        yield _find_first_video_id(lockup), _lockup_title(lockup)


def _walk_lockup_view_models(value: Any):
    if isinstance(value, dict):
        lockup = value.get("lockupViewModel")
        if isinstance(lockup, dict):
            yield lockup
        for child in value.values():
            yield from _walk_lockup_view_models(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_lockup_view_models(child)


def _renderer_title(renderer: dict[str, Any]) -> str:
    title = renderer.get("title", {})
    if "simpleText" in title:
        return html.unescape(title["simpleText"])
    runs = title.get("runs", [])
    if runs and "text" in runs[0]:
        return html.unescape(runs[0]["text"])
    return ""


def _lockup_title(lockup: dict[str, Any]) -> str:
    title = (
        lockup.get("metadata", {})
        .get("lockupMetadataViewModel", {})
        .get("title", {})
        .get("content", "")
    )
    return html.unescape(title)


def _find_first_video_id(value: Any) -> str:
    if isinstance(value, dict):
        video_id = value.get("videoId")
        if isinstance(video_id, str):
            return video_id
        for child in value.values():
            found = _find_first_video_id(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first_video_id(child)
            if found:
                return found
    return ""


def _entry_video_id(entry: Any) -> str:
    yt_video_id = entry.get("yt_videoid")
    if yt_video_id:
        return yt_video_id

    entry_id = entry.get("id", "")
    if entry_id.startswith("yt:video:"):
        return entry_id.removeprefix("yt:video:")

    link = entry.get("link", "")
    if "v=" in link:
        return link.split("v=", 1)[1].split("&", 1)[0]

    raise ValueError(f"Could not find video id in RSS entry: {entry}")


def _entry_published_at(entry: Any) -> str:
    parsed = entry.get("published_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return entry.get("published", "")
