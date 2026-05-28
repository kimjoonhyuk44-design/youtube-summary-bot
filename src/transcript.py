from __future__ import annotations

import sys
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api.formatters import TextFormatter


PREFERRED_LANGUAGES = ("ko", "en")


@dataclass(frozen=True)
class TranscriptResult:
    video_id: str
    text: str
    language_code: str
    is_generated: bool


def fetch_transcript(video_id: str) -> TranscriptResult | None:
    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
        transcript = _pick_transcript(transcript_list)
        if transcript is None:
            return None

        fetched = transcript.fetch()
        language_code = transcript.language_code
        is_generated = transcript.is_generated
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        return None
    except Exception as error:
        print(f"Transcript fetch failed for {video_id}: {error}")
        return None

    formatter = TextFormatter()
    text = formatter.format_transcript(fetched).strip()

    return TranscriptResult(
        video_id=video_id,
        text=text,
        language_code=language_code,
        is_generated=is_generated,
    )


def _pick_transcript(transcript_list):
    for language_code in PREFERRED_LANGUAGES:
        try:
            return transcript_list.find_transcript([language_code])
        except Exception:
            pass

    for language_code in PREFERRED_LANGUAGES:
        try:
            return transcript_list.find_generated_transcript([language_code])
        except Exception:
            pass

    for transcript in transcript_list:
        return transcript

    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python src/transcript.py VIDEO_ID")

    result = fetch_transcript(sys.argv[1])
    if result is None:
        print("No transcript found")
        return

    source = "auto-generated" if result.is_generated else "manual"
    print(f"Transcript found: {len(result.text)} characters")
    print(f"Language: {result.language_code} ({source})")
    print()
    print(result.text[:1000])


if __name__ == "__main__":
    main()
