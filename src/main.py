from __future__ import annotations

import json
import os
from pathlib import Path

from summarize import can_summarize, format_summary_message, summarize_video
from telegram import can_send_telegram, send_telegram_message
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
    summarizer_ready = can_summarize()
    telegram_ready = can_send_telegram()
    test_video_id = os.environ.get("TEST_VIDEO_ID", "").strip()
    telegram_test = os.environ.get("TELEGRAM_TEST", "").lower() == "true"

    print(f"Loaded {len(channels)} channel(s)")
    if not summarizer_ready:
        print("OPENAI_API_KEY is not set. Summaries will be skipped.")
    if not telegram_ready:
        print("Telegram secrets are not set. Messages will only be printed.")

    if telegram_test:
        _send_telegram_test(telegram_ready)
        return

    if test_video_id:
        print(f"Manual test mode for video: {test_video_id}")
        video = Video(
            channel_id="manual",
            channel_name="Manual Test",
            video_id=test_video_id,
            title=f"Manual test video {test_video_id}",
            url=f"https://www.youtube.com/watch?v={test_video_id}",
            published_at="",
        )
        _process_video(video, summarizer_ready, telegram_ready)
        print("Manual test complete. seen_videos.json was not updated.")
        return

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
            processed = _process_video(video, summarizer_ready, telegram_ready)
            if processed:
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


def _process_video(
    video: Video, summarizer_ready: bool, telegram_ready: bool
) -> bool:
    print(f"- {video.title}")
    print(f"  {video.url}")

    transcript = fetch_transcript(video.video_id)
    if transcript is None:
        print("  Transcript: not found")
        if telegram_ready:
            send_telegram_message(
                "\n".join(
                    [
                        "[요약 생략]",
                        "",
                        f"제목: {video.title}",
                        f"링크: {video.url}",
                        "",
                        "사유: 자막을 가져오지 못했습니다. GitHub Actions 서버 IP가 YouTube 자막 요청에서 차단됐거나, 영상에 사용 가능한 자막이 없을 수 있습니다.",
                    ]
                )
            )
            print("  Telegram: sent transcript failure notice")
        return True

    source = "auto-generated" if transcript.is_generated else "manual"
    print(
        "  Transcript: "
        f"{len(transcript.text)} characters "
        f"({transcript.language_code}, {source})"
    )

    if not summarizer_ready:
        print("  Summary: skipped because OPENAI_API_KEY is not set")
        return False

    summary = summarize_video(video.title, video.url, transcript.text)
    message = format_summary_message(video.title, video.url, summary)
    print("  Summary:")
    print(_indent(message, "    "))

    if telegram_ready:
        send_telegram_message(message)
        print("  Telegram: sent")
    else:
        print("  Telegram: skipped because secrets are not set")

    return True


def _send_telegram_test(telegram_ready: bool) -> None:
    print("Telegram test mode")
    message = "YouTube summary bot Telegram test: 연결 확인 완료"
    if telegram_ready:
        send_telegram_message(message)
        print("Telegram: sent")
    else:
        print("Telegram: skipped because secrets are not set")


def _indent(text: str, prefix: str) -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())


if __name__ == "__main__":
    main()
