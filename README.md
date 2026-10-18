
## Manual title and reliable video sending

If the filename cannot identify a title or no artwork is found, the bot now asks for a movie/series name instead of stopping. Reply with the name; IMDb buttons appear. After selecting a result, the bot sends the artwork preview with a **Done - use this thumbnail** button. Only after Done is pressed does it download the original file and send it again with the selected thumbnail.

The bot uses `ffprobe` on the downloaded file, not only the file extension. Therefore a video uploaded as a Telegram document is detected as video even when it is MKV, MP4, MP4M, WEBM, MOV, AVI, TS or another container that ffprobe understands. It sends the result with `send_video`, the thumbnail, video width/height, and rounded duration, so Telegram should display the real duration instead of `00:00`. Non-video documents remain documents and still receive the thumbnail where Telegram supports it.

Progress messages are edited no more than once every five seconds. The Docker image installs `ffmpeg`/`ffprobe` for metadata detection.

## Advanced UI and management features

The current build includes a per-user SQLite settings database. Use `/settings` to select rename format (`Title [Quality]`, `[Quality] Title`, or title only), thumbnail quality, watermark presets, Sinhala badge, send mode (`auto`, `video`, or `document`), and reset defaults. `/watermark Your Channel` sets a custom watermark; `/watermark off` disables it.

The file workflow exposes owner-only normal-name and Sinhala-subtitle-name actions, a cancel button, a thumbnail gallery when several landscape images are found, and a five-second throttled progress display. `/cancel` cancels the caller's pending/active jobs; users cannot cancel another user's job. Per-chat serialization and per-user active-job limits prevent overlapping uploads from corrupting state.

Available commands include `/start`, `/settings`, `/thumb`, `/search`, `/status`, `/queue`, `/history`, `/cancel`, `/admin`, `/users`, and `/clearqueue`. Search results are paginated. Series names with `S02E03` are parsed into season and episode details. Completed jobs are stored in SQLite and produce a detailed report containing title, quality, filename resolution label, duration, size, thumbnail source, output name, and total time.

Set these optional Hugging Face variables for access control:

```text
ADMIN_IDS=123456789
ALLOWED_USER_IDS=123456789,987654321
MAX_ACTIVE_JOBS_PER_USER=2
DB_PATH=/tmp/sadesha-bot.sqlite3
```

If `ALLOWED_USER_IDS` is empty, all users may use normal features. `ADMIN_IDS` is required for `/admin`, `/users`, and `/clearqueue`.

## Transfer speed tuning

The Docker build now starts Pyrogram with 32 update workers and up to 4 concurrent MTProto transmissions. Pyrogram's large-file uploader already uses four parallel upload workers internally for files above 10 MB, and `tgcrypto` is included. Progress message edits remain throttled so they do not add a Telegram request for every chunk.

Set `PYROGRAM_WORKERS=32` and `MAX_CONCURRENT_TRANSMISSIONS=4` in the Space variables. One chat is intentionally serialized so two files from the same user do not corrupt each other's status or temporary files. Different chats can use the transmission pool concurrently.

A fixed 100 Mbps cannot be guaranteed by Python code. The actual rate is limited by the Hugging Face Space's network path, Telegram's MTProto data centre, source file routing, CPU, and disk I/O. Because this bot changes the filename and applies a new thumbnail, it must download the source and upload a new copy; Telegram cannot reuse the original file ID for that transformed upload. If the server route is slower than 100 Mbps, no client setting can force that rate.

## Advanced batch queue and failed-item recovery

Start a batch with `/batch`. Choose the Sinhala tag once, then forward or send up to 50 files. Files are only collected while the batch is in collecting mode, so ordinary uploads remain on the normal flow. Send `/batchdone` to start sequential processing. Each item is searched, downloaded, uploaded, and then the worker waits exactly 20 seconds before starting the next item.

A missing IMDb result or missing landscape artwork is recorded as a failed item and does not stop the batch. At the end, the bot sends a summary with one `Fix` button per failed file. Press Fix, send the correct movie/series name, select the IMDb result, choose the thumbnail/name option, and press Done. `/cancelbatch` clears the queue and failed list and cancels the batch worker. The batch limit is 50 files.

The false active-job limit is fixed: only real active processing jobs count toward `MAX_ACTIVE_JOBS_PER_USER`; expired pending UI selections are pruned after 15 minutes. Failed item recovery is owner-only.

## IMDb formatted captions and branding

Before the transformed file is uploaded, the bot reads public IMDb title-page JSON-LD and then fills missing fields through the no-key IMDb-ID Cinemeta fallback. The caption includes an HTML-formatted title/year, IMDb rating and star display, genres, director, main cast, writer, country, release date, awards, story, quality, filename resolution, audio/subtitle label, duration, file size, and a clickable IMDb ID. If a source is unavailable, a safe compact fallback caption is used and the upload continues.

Each video/document gets a `Watch Trailer` button. Without a YouTube API key, the button opens a title/year-specific YouTube official-trailer search; this is deliberate rather than inventing an unverified trailer URL. The uploaded caption uses HTML parse mode.

A transparent AI-designed `sadesha_sub_logo_ai_neon.png` is now the default overlay. It combines flowing teal/gold calligraphy, film reel, film strip, flowers, sparkles, and a cinema ticket. It is placed at the top-right corner of the thumbnail. A separate transparent `sadesha_sub_line_neon.png` asset sits directly beneath it, so the `Sadesha.Sub` line is an actual PNG overlay rather than plain text drawn by Pillow. The Gold and Royal variants remain available as alternatives. Select the logo and line with `LOGO_PATH` and `LINE_PATH`.

Additional transparent PNGs can be supplied through `OVERLAY_PATHS=/home/user/app/badge.png,/home/user/app/frame.png`; the first available overlay is used if the main logo path is unavailable. The bundled logo remains the default so no extra key or API is required.

## Channel send buttons

After a processed video/document is uploaded, its post includes `📤 Send to Channel`. Press it, use `➕ Add Channel`, then send the channel `@username` or numeric `-100...` ID. The user must be a channel administrator and the bot must already be an administrator. Saved channels appear in a private list, and the processed post can be copied to any selected channel without a forwarded-message tag. Use `/channels` to manage the saved list and remove channels. Telegram does not allow a bot to open the user's private channel picker or promote itself; the explicit admin check prevents unauthorized posting.

For private channels without a username, press `➕ Add Channel` and forward any post from that channel to the bot. The bot resolves the forwarded channel ID, verifies both the user's and bot's administrator status, and saves it. The bot now registers the complete command menu automatically at startup. Transfer speed settings remain enabled through `PYROGRAM_WORKERS=32` and `MAX_CONCURRENT_TRANSMISSIONS=4`; the `/status` output and startup log show these settings.
