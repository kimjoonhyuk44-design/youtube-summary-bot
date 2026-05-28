from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI


DEFAULT_MODEL = "gpt-4o-mini"
MAX_TRANSCRIPT_CHARS = 50000


SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "array",
            "items": {"type": "string"},
        },
        "mentioned_companies_or_stocks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "ticker": {"type": "string"},
                    "market": {"type": "string"},
                    "reason": {"type": "string"},
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative", "mixed", "unknown"],
                    },
                },
                "required": ["name", "ticker", "market", "reason", "sentiment"],
            },
        },
        "dates_or_events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "date": {"type": "string"},
                    "event": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["date", "event", "context"],
            },
        },
        "investment_points": {
            "type": "array",
            "items": {"type": "string"},
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "disclaimer": {"type": "string"},
    },
    "required": [
        "summary",
        "mentioned_companies_or_stocks",
        "dates_or_events",
        "investment_points",
        "risks",
        "disclaimer",
    ],
}


@dataclass(frozen=True)
class VideoSummary:
    summary: list[str]
    mentioned_companies_or_stocks: list[dict[str, str]]
    dates_or_events: list[dict[str, str]]
    investment_points: list[str]
    risks: list[str]
    disclaimer: str


def can_summarize() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def summarize_video(title: str, url: str, transcript: str) -> VideoSummary:
    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    clipped_transcript = transcript[:MAX_TRANSCRIPT_CHARS]

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You summarize Korean YouTube investment/economy videos. "
                    "Extract only information supported by the transcript. "
                    "If a ticker, market, date, or event is not explicit, use an empty string. "
                    "Do not provide personal financial advice."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Video title: {title}\n"
                    f"Video URL: {url}\n\n"
                    "Transcript:\n"
                    f"{clipped_transcript}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "youtube_investment_summary",
                "strict": True,
                "schema": SUMMARY_SCHEMA,
            }
        },
    )

    data = json.loads(response.output_text)
    return VideoSummary(**data)


def format_summary_message(title: str, url: str, summary: VideoSummary) -> str:
    lines = [f"[신규 영상 요약]", "", f"제목: {title}", f"링크: {url}", ""]

    lines.append("핵심 요약:")
    lines.extend(f"- {item}" for item in summary.summary)

    if summary.mentioned_companies_or_stocks:
        lines.extend(["", "언급 종목/기업:"])
        for item in summary.mentioned_companies_or_stocks:
            ticker = f" ({item['ticker']})" if item["ticker"] else ""
            market = f" / {item['market']}" if item["market"] else ""
            lines.append(
                f"- {item['name']}{ticker}{market}: "
                f"{item['reason']} [{item['sentiment']}]"
            )

    if summary.dates_or_events:
        lines.extend(["", "일정/이벤트:"])
        for item in summary.dates_or_events:
            date = item["date"] or "날짜 미상"
            lines.append(f"- {date}: {item['event']} ({item['context']})")

    if summary.investment_points:
        lines.extend(["", "투자 포인트:"])
        lines.extend(f"- {item}" for item in summary.investment_points)

    if summary.risks:
        lines.extend(["", "리스크:"])
        lines.extend(f"- {item}" for item in summary.risks)

    lines.extend(["", summary.disclaimer])
    return "\n".join(lines)
