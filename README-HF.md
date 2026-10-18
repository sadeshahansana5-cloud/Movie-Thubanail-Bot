---
title: Sadesha Films Fanart Thumbnail Bot
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Sadesha Films Fanart.tv Thumbnail Bot

Pyrogram bot that uses IMDb title lookup and Fanart.tv title-art images. TMDB is not used.

## Commands

- Upload a movie/series file. The bot parses the filename and sends it back with a Telegram-compatible thumbnail.
- `/thumb Movie Name` — search and send the artwork only.
- `/search Movie Name` — show IMDb title candidates.
- `/status` — test configuration and IMDb connectivity.

## Environment secrets

- `API_ID` — Telegram API ID from `my.telegram.org`
- `API_HASH` — Telegram API hash from `my.telegram.org`
- `BOT_TOKEN` — token from `@BotFather`
- `FANART_API_KEY` — Fanart.tv API key
- `FANART_CLIENT_KEY` — optional personal Fanart.tv client key
- `TVDB_API_KEY` — TheTVDB v4 API key, required for TV series lookup
- `TVDB_PIN` — optional TVDB subscriber PIN
- No image-search API key is required; the fallback uses a public Yandex image-results page.
- `MAX_FILE_MB` — optional, default `2048`

No `TMDB_API_KEY` is required.

## Artwork selection

Movies use IMDb suggestion search to get an IMDb ID, then Fanart.tv's movie endpoint. Series use IMDb title search, TheTVDB v4 search to get a TVDB ID, then Fanart.tv's TV endpoint. The bot prefers `moviethumb`/`tvthumb`, then `moviebanner`/`tvbanner`, filtered to roughly 16:9 assets. If Fanart.tv has no match and `BRAVE_API_KEY` is set, it searches the web for an existing 16:9 image and does not add synthetic title text.

Fanart.tv has no general title-only API lookup; it requires the supported movie or TV identifier. That is why the ID lookup steps are necessary.

The Docker Space listens on port `7860`. Downloaded media is deleted after sending; no persistent storage is required for normal operation. Follow all source-service and media rights terms.
