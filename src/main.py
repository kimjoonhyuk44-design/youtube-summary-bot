from __future__ import annotations

import json
from pathlib import Path

from transcript import fetch_transcript
from youtube_rss import Video, fetch_latest_videos


ROOT = Path(__file__).resolve().parents[1]
CHANNELS_PATH = ROOT / "channels.json"
SEEN_PATH = ROOT / "seen_videos.json"
MAX_VIDEOS_PER_CHANNEL = 5


def main() -> None:
    channels = _load_json(CHANNELS_PATH)
    seen = _load_seen()
    found_new = False

    print(f"Loaded {len(channels)} channel(s)")

    for channel in channels:
        print(f"Checking {channel['name']} ({channel['channel_id']})")
        videos = fetch_latest_videos(channel, limit=MAX_VIDEOS_PER_CHANNEL)
        new_videos = _filter_new_videos(videos, seen)

        if not new_videos:
            print("No new videos")
            continue

        found_new = True
        print(f"Found {len(new_videos)} new video(s)")
        for video in new_videos:
            print(f"- {video.title}")
            print(f"  {video.url}")
            transcript = fetch_transcript(video.video_id)
            if transcript is None:
                print("  Transcript: not found")
            else:
                source = "auto-generated" if transcript.is_generated else "manual"
                print(
                    "  Transcript: "
                    f"{len(transcript.text)} characters "
                    f"({transcript.language_code}, {source})"
                )
            seen.setdefault(video.channel_id, [])
            seen[video.channel_id].append(video.video_id)

    if found_new:
        _save_json(SEEN_PATH, seen)
        print("Updated seen_videos.json")
    else:
        print("Nothing to update")


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _load_seen() -> dict[str, list[str]]:
    if not SEEN_PATH.exists():
        return {}
    data = _load_json(SEEN_PATH)
    return {channel_id: list(video_ids) for channel_id, video_ids in data.items()}


def _save_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _filter_new_videos(videos: list[Video], seen: dict[str, list[str]]) -> list[Video]:
    new_videos = []
    for video in videos:
        if video.video_id not in seen.get(video.channel_id, []):
            new_videos.append(video)
    return new_videos


if __name__ == "__main__":
    main()
