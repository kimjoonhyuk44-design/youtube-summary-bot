# YouTube Summary Messenger Bot

Subscribed-channel style YouTube RSS watcher that summarizes new videos and sends the result to a messenger.

## MVP Scope

- Check configured YouTube channel RSS feeds once per day with GitHub Actions.
- Skip videos that were already processed.
- Use captions/transcripts only; no audio download.
- Send summaries to Telegram.

## Files

- `channels.json`: YouTube channels to watch.
- `seen_videos.json`: Processed video IDs, committed by GitHub Actions.
- `.github/workflows/daily.yml`: Scheduled workflow placeholder.

