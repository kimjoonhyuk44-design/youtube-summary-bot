from __future__ import annotations

import os

import requests


MAX_TELEGRAM_MESSAGE_LENGTH = 4096


def can_send_telegram() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_telegram_message(message: str) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    for chunk in _split_message(message):
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        response.raise_for_status()


def _split_message(message: str) -> list[str]:
    if len(message) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return [message]

    chunks: list[str] = []
    current = ""
    for line in message.splitlines():
        next_current = f"{current}\n{line}" if current else line
        if len(next_current) > MAX_TELEGRAM_MESSAGE_LENGTH:
            if current:
                chunks.append(current)
            current = line
        else:
            current = next_current

    if current:
        chunks.append(current)

    return chunks
