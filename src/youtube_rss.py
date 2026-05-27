from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

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
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(feed_url)

    if getattr(feed, "bozo", False):
        raise RuntimeError(f"Failed to parse RSS feed for {channel_name}: {feed_url}")

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

