<div align="center">

# 🎬 Sadesha Films Thumbnail & Media Bot

**Automatic movie/series identification, landscape artwork search, Telegram thumbnail processing, smart renaming and channel publishing.**

<p>
  <img src="sadesha_sub_logo_ai_neon.png" width="240" alt="Sadesha Films logo">
</p>

<p>
  <a href="https://docs.pyrogram.org/"><img src="https://img.shields.io/badge/Pyrogram-2.0.106-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Pyrogram"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://ffmpeg.org/documentation.html"><img src="https://img.shields.io/badge/FFmpeg-FFprobe-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg"></a>
  <a href="https://docs.docker.com/"><img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="https://huggingface.co/docs/hub/spaces"><img src="https://img.shields.io/badge/Hugging%20Face-Spaces-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face Spaces"></a>
</p>

**Developer:** Sadesha Hansana  
**Brand:** Sadesha Films

</div>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0B132B,45:1C7C8C,100:FFD166&height=170&section=header&text=SADesha%20Films&fontSize=54&fontColor=ffffff&animation=twinkling&fontAlignY=38&desc=Smart%20Telegram%20Movie%20Thumbnail%20Automation&descSize=18&descAlignY=62" width="100%" alt="Animated Sadesha Films header">
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=19&pause=900&color=00E5FF&center=true&vCenter=true&width=800&height=60&lines=Find+the+right+movie+or+series;Preview+before+sending;Choose+the+best+landscape+thumbnail;Rename+%2B+upload+%2B+publish+to+channels" alt="Animated feature typing banner">
</p>

<p align="center">
  <a href="https://docs.pyrogram.org/"><img src="https://img.shields.io/badge/📚%20Official%20Docs-Pyrogram-00BFFF?style=for-the-badge" alt="Pyrogram docs"></a>
  <a href="https://huggingface.co/docs/hub/spaces-sdks-docker"><img src="https://img.shields.io/badge/🚀%20Deploy-Hugging%20Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Deploy on Hugging Face"></a>
  <a href="https://core.telegram.org/bots/api"><img src="https://img.shields.io/badge/🤖%20Telegram-Bot%20API-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot API"></a>
  <a href="https://ffmpeg.org/documentation.html"><img src="https://img.shields.io/badge/🎞%20Media-FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg docs"></a>
</p>

<p align="center">
  <a href="#-visual-feature-map">✨ Features</a> ·
  <a href="#-commands">⌨️ Commands</a> ·
  <a href="#-deploy-on-hugging-face-spaces">☁️ Deploy</a> ·
  <a href="#-official-documentation">📚 Docs</a> ·
  <a href="#-developer">👨‍💻 Developer</a>
</p>

## 🧭 Quick action buttons

| 🎬 Bot workflow | 🛠 Technology | 📣 Publishing | 🎨 Branding |
|---|---|---|---|
| [Thumbnail search](#-manual-thumbnail-search) · [File flow](#-how-the-file-workflow-works) | [Pyrogram](https://docs.pyrogram.org/) · [Python](https://docs.python.org/3/) · [Pillow](https://pillow.readthedocs.io/en/stable/) | [Telegram Bot API](https://core.telegram.org/bots/api) · [Channel workflow](#-channel-publishing) | [Logo assets](#-thumbnail-processing) · [Settings](#%EF%B8%8F-settings) |

## ✨ Visual feature map

<table>
<tr>
<td align="center" width="25%"><img src="https://img.icons8.com/fluency/96/search.png" width="58" alt="Search"><br><b>Smart Search</b><br><sub>IMDb result buttons and title recovery</sub></td>
<td align="center" width="25%"><img src="https://img.icons8.com/fluency/96/picture.png" width="58" alt="Artwork"><br><b>Artwork Gallery</b><br><sub>Landscape artwork with preview selection</sub></td>
<td align="center" width="25%"><img src="https://img.icons8.com/fluency/96/video.png" width="58" alt="Video"><br><b>Media Engine</b><br><sub>FFmpeg, FFprobe and real duration</sub></td>
<td align="center" width="25%"><img src="https://img.icons8.com/fluency/96/send.png" width="58" alt="Send"><br><b>Channel Send</b><br><sub>Saved public and private channels</sub></td>
</tr>
</table>

<details>
<summary><b>🎨 Open the branding gallery</b></summary>

<p align="center">
  <img src="sadesha_sub_logo_ai_neon.png" width="230" alt="Neon logo">
  <img src="sadesha_sub_logo_ai_gold.png" width="230" alt="Gold logo">
  <img src="sadesha_sub_logo_ai_royal.png" width="230" alt="Royal logo">
</p>

<p align="center"><img src="sadesha_sub_line_neon.png" width="760" alt="Sadesha.Sub line"></p>

</details>

---

## 📌 About this project

Sadesha Films Thumbnail & Media Bot is a Pyrogram-based Telegram bot for movie and series file management. It reads a filename, identifies the likely title, finds candidate IMDb results, searches for landscape artwork, shows a preview, lets the user choose the correct image, adds a Telegram-compatible thumbnail, renames the file and sends it back as a video or document.

The bot is designed for Hugging Face Docker Spaces, but it can also run on a Linux VPS or a local Docker installation.

> **Important:** This README documents the features implemented in this repository. It does not claim subtitle hardcoding, video re-encoding, billing, credits, Mini Apps or other features that are not part of this codebase.

<a id="main-features"></a>
<p align="center"><img src="readme_assets/features.svg" width="100%" alt="Main features banner"></p>

### 🎞 Movie and series workflow

- Automatic filename cleanup for common release names such as `WEB-DL`, `WEBRip`, `BluRay`, `HDRip`, `720p`, `1080p`, `S01E03`, channel usernames and website prefixes.
- IMDb suggestion search with multiple result buttons showing title, year and Movie/Series type.
- Series parsing for season and episode patterns such as `Breaking.Bad.S02E03.1080p.mkv`.
- Manual title recovery when the filename is unclear or the automatic lookup fails.
- Landscape artwork search with Fanart.tv when configured, followed by a no-key public image-search fallback.
- 16:9-style image filtering and a preview gallery with `Use`, `Next` and `Cancel` controls.
- The bot does not silently send the first questionable image anymore; users can inspect the preview first.

### 🖼 Thumbnail processing

- Telegram-compatible thumbnail generation.
- Automatic resize and JPEG output for Telegram media uploads.
- Small top-right neon logo overlay.
- Separate transparent `Sadesha.Sub` line asset below the logo.
- Logo ON/OFF control from `/settings`.
- Bundled Neon, Gold and Royal logo assets.
- Optional custom PNG overlays through `OVERLAY_PATHS`.
- Thumbnail quality settings: Optimized, Low, Medium and High.

<p align="center">
  <img src="sadesha_sub_line_neon.png" width="720" alt="Sadesha.Sub transparent line asset">
</p>

### 📁 File rename and metadata

- Preserves the original extension.
- Uses the selected movie/series title and the quality label detected from the filename.
- Supports rename formats such as `Title [Quality]`, `[Quality] Title` and title only.
- Detects quality from the filename instead of incorrectly guessing it from the actual resolution.
- Detects resolution labels such as `480p`, `720p`, `1080p`, `2160p` and `4K`.
- Detects Sinhala subtitle indicators and can add a Sinhala subtitle label.
- Removes common Telegram channel names, usernames, site prefixes, emoji and release noise.

### 📊 Media details and captions

- Uses `ffprobe` after download to detect whether a document is actually a video.
- Reads duration, video dimensions and file size.
- Sends video media as video when possible and retains document mode when selected.
- Generates an HTML-formatted caption containing title, year, IMDb rating, genres, director, cast, writer, country, release date, awards, story, quality, resolution, audio/subtitle label, duration and file size.
- Adds a clickable IMDb ID link.
- Adds a trailer button using a verified trailer ID when available, otherwise a title-specific YouTube official-trailer search link.
- Uses safe fallback captions when metadata services are unavailable.

### ⚡ Progress, speed and reliability

- Live download and upload progress messages.
- Progress updates are throttled to avoid excessive Telegram requests.
- Five-second progress edit interval.
- Pyrogram update workers and concurrent transmission settings are configurable.
- Per-chat serialization prevents two jobs in the same chat from corrupting status or temporary files.
- Per-user active-job limits.
- Owner-only cancellation buttons.
- Temporary downloaded files are removed after processing.
- `/status` reports uptime, RAM peak, CPU load, disk usage, FFmpeg/FFprobe availability, active jobs and queue information.

<p align="center"><img src="readme_assets/batch.svg" width="100%" alt="Advanced batch banner"></p>

### 📦 Batch processing

- `/batch` starts a batch collection session.
- Up to 50 files can be forwarded or uploaded.
- Sinhala subtitle preference is asked once for the entire batch.
- `/batchdone` starts sequential processing.
- A 20-second delay is applied between completed batch items.
- Missing title/artwork items are collected into a failed list instead of stopping the whole batch.
- End-of-batch summary with individual `Fix` buttons.
- A failed item can be repaired by entering the correct title and selecting a new artwork.
- `/cancelbatch` clears the active batch, queue and failed list.

### 📣 Channel publishing

- Save multiple destination channels.
- Supports public channels using `@username`.
- Supports numeric channel IDs such as `-1001234567890`.
- Supports private channels by forwarding a post from the private channel while Add Channel mode is active.
- Verifies that the user is a channel administrator.
- Verifies that the bot is an administrator in the destination channel.
- Processed posts include a `Send to Channel` button.
- Channel posting does not depend on a forwarded-message tag.
- Saved channels can be selected or removed from the channel panel.

<p align="center"><img src="readme_assets/settings.svg" width="100%" alt="Smart settings banner"></p>

### ⚙️ Settings

`/settings` includes:

- Rename format
- Thumbnail quality
- Thumbnail logo ON/OFF
- Text watermark presets and custom watermark command
- Sinhala subtitle badge ON/OFF
- Automatic/video/document send mode
- Progress ON/OFF
- Reset all defaults

### 📚 Built-in documentation and asset gallery

The `/start` menu contains:

- Official Docs buttons
- Pyrogram documentation and PyPI
- Python documentation
- Pillow documentation
- FFmpeg and FFprobe documentation
- Docker documentation
- Hugging Face Spaces documentation
- Telegram Bot API and FAQ
- IMDb and Fanart.tv API pages
- Developer/About panel
- Branding asset preview gallery
- Quick Help panel

---

<a id="how-the-file-workflow-works"></a>
<p align="center"><img src="readme_assets/workflow.svg" width="100%" alt="How it works banner"></p>

```text
Send file
   │
   ├── Clean filename
   ├── Detect title, year, quality, resolution and season/episode
   ├── Search IMDb candidates
   ├── Search landscape artwork
   ├── Show thumbnail preview
   │      ├── Use this thumbnail
   │      ├── Next thumbnail
   │      └── Cancel
   ├── Ask normal name or Sinhala subtitle name
   ├── Download source file
   ├── Read media metadata with ffprobe
   ├── Rename and add Telegram thumbnail
   ├── Upload as video or document
   └── Show final caption, trailer and channel buttons
```

## 🎛 Visual command panel

<p align="center">
  <a href="#-commands"><img src="https://img.shields.io/badge/▶%20START-/start-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Start"></a>
  <a href="#-manual-thumbnail-search"><img src="https://img.shields.io/badge/🖼%20THUMB-/thumb-8A2BE2?style=for-the-badge" alt="Thumbnail"></a>
  <a href="#%EF%B8%8F-settings"><img src="https://img.shields.io/badge/⚙%20SETTINGS-/settings-00A86B?style=for-the-badge" alt="Settings"></a>
  <a href="#-channel-publishing"><img src="https://img.shields.io/badge/📣%20CHANNELS-/channels-FF8C00?style=for-the-badge" alt="Channels"></a>
  <a href="#-batch-processing"><img src="https://img.shields.io/badge/📦%20BATCH-/batch-E91E63?style=for-the-badge" alt="Batch"></a>
</p>

<a id="commands"></a>
<p align="center"><img src="readme_assets/commands.svg" width="100%" alt="Command center banner"></p>

| Command | Description |
|---|---|
| `/start` | Open the main menu, docs, help and branding panels |
| `/settings` | Open per-user settings |
| `/watermark TEXT` | Set a custom text watermark |
| `/watermark off` | Disable the text watermark |
| `/thumb Movie Name` | Search artwork and choose a thumbnail manually |
| `/search Movie Name` | Show IMDb title candidates |
| `/channels` | Manage saved channels |
| `/status` | Show server, media tools, queue and job status |
| `/queue` | Show current jobs |
| `/history` | Show completed job history |
| `/cancel` | Cancel your current job |
| `/batch` | Start a batch collection session |
| `/batchdone` | Start the collected batch |
| `/cancelbatch` | Cancel and clear the active batch |
| `/admin` | Show admin controls when the user is configured as an admin |
| `/users` | Admin user list |
| `/clearqueue` | Admin queue cleanup |

## 🖼 Manual thumbnail search

```text
/thumb Moana 2026
```

The bot first shows IMDb candidates. After choosing the title, it displays the first landscape image as a photo preview. Use `Next thumbnail` to cycle through available artwork. The selected image is only sent after pressing `Use this thumbnail`.

<a id="deploy-on-hugging-face-spaces"></a>
<p align="center"><img src="readme_assets/deploy.svg" width="100%" alt="Deployment banner"></p>

### 1. Create the Space

Create a new Hugging Face Space with:

- SDK: Docker
- Port: `7860`
- Hardware: CPU is sufficient for thumbnail processing; larger files benefit from more RAM and faster disk

### 2. Upload these files

```text
app.py
Dockerfile
requirements-hf.txt
sadesha_sub_logo.png
sadesha_sub_logo_ai_neon.png
sadesha_sub_logo_ai_gold.png
sadesha_sub_logo_ai_royal.png
sadesha_sub_line_neon.png
sadesha_sub_line_gold.png
```

### 3. Add Space Secrets / Variables

Required:

```text
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
BOT_TOKEN=your_botfather_token
```

Recommended:

```text
ADMIN_IDS=123456789
ALLOWED_USER_IDS=
MAX_FILE_MB=2048
MAX_ACTIVE_JOBS_PER_USER=2
PYROGRAM_WORKERS=32
MAX_CONCURRENT_TRANSMISSIONS=4
DB_PATH=/tmp/sadesha-bot.sqlite3
LOGO_PATH=/home/user/app/sadesha_sub_logo_ai_neon.png
LINE_PATH=/home/user/app/sadesha_sub_line_neon.png
OVERLAY_PATHS=
PORT=7860
```

Optional artwork services:

```text
FANART_API_KEY=
FANART_CLIENT_KEY=
TVDB_API_KEY=
TVDB_PIN=
```

No TMDB API key is required by this project. Fanart.tv and TVDB keys improve artwork availability, but the public image-search fallback can work without an image-search API key.

### 4. Rebuild

After uploading or changing files, use **Factory Rebuild** or restart the Space. Then send `/start` to the bot and open the new Docs, Settings and Branding Assets panels.

## 🐳 Local Docker deployment

```bash
docker build -t sadesha-films-bot .
docker run --rm \
  -e API_ID="your_api_id" \
  -e API_HASH="your_api_hash" \
  -e BOT_TOKEN="your_bot_token" \
  -e ADMIN_IDS="123456789" \
  -p 7860:7860 \
  sadesha-films-bot
```

## 🐍 Local Python deployment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-hf.txt
sudo apt-get update && sudo apt-get install -y ffmpeg
export API_ID="your_api_id"
export API_HASH="your_api_hash"
export BOT_TOKEN="your_bot_token"
python app.py
```

## 🔐 Security and privacy

- Never commit `API_ID`, `API_HASH`, `BOT_TOKEN` or service API keys.
- Put secrets in Hugging Face Secrets or environment variables.
- Restrict access with `ALLOWED_USER_IDS` when the bot is private.
- Add your own Telegram ID to `ADMIN_IDS` before using admin commands.
- The bot must be an administrator in any channel where it posts.
- Temporary downloaded media is stored in a temporary directory and removed after processing.
- Respect copyright, source-site terms and Telegram terms when handling media.

## 🔧 Troubleshooting

### `sqlite3.OperationalError: unable to open database file`

Use a writable path such as:

```text
DB_PATH=/tmp/sadesha-bot.sqlite3
PYROGRAM_WORKDIR=/tmp/sadesha-pyrogram
```

### Bot starts but commands do not appear

Wait for startup to complete, restart the bot, open the chat again and send `/start`. Commands are registered automatically after the Pyrogram client starts.

### Thumbnail is unavailable

Use `/thumb Movie Name` and choose another IMDb result or another image with `Next thumbnail`. For series artwork, adding Fanart.tv and TVDB credentials improves results.

### Channel cannot be added

The user must be an administrator and the bot must be an administrator. For a private channel, press Add Channel and forward a post from that channel instead of typing a username.

### Upload speed is lower than expected

The values `PYROGRAM_WORKERS=32` and `MAX_CONCURRENT_TRANSMISSIONS=4` enable aggressive client-side concurrency, but a fixed 100 Mbps cannot be guaranteed. Hugging Face routing, Telegram data centre limits, CPU, disk and source-server speed still apply.

### FFprobe returns no duration

Make sure `ffmpeg` is installed in the Docker image and that the uploaded file is a valid media container. The bot checks the actual stream with `ffprobe`, not only the filename extension.

<a id="official-documentation"></a>
<p align="center"><img src="readme_assets/docs.svg" width="100%" alt="Official documentation banner"></p>

<table align="center">
<tr>
<td align="center"><a href="https://docs.pyrogram.org/"><img src="https://img.shields.io/badge/Pyrogram-Documentation-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Pyrogram documentation"></a></td>
<td align="center"><a href="https://pypi.org/project/Pyrogram/"><img src="https://img.shields.io/badge/Pyrogram-PyPI-3775A9?style=for-the-badge&logo=pypi&logoColor=white" alt="Pyrogram on PyPI"></a></td>
<td align="center"><a href="https://docs.python.org/3/"><img src="https://img.shields.io/badge/Python-Documentation-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python documentation"></a></td>
</tr>
<tr>
<td align="center"><a href="https://pillow.readthedocs.io/en/stable/"><img src="https://img.shields.io/badge/Pillow-Documentation-306998?style=for-the-badge&logo=python&logoColor=white" alt="Pillow documentation"></a></td>
<td align="center"><a href="https://ffmpeg.org/documentation.html"><img src="https://img.shields.io/badge/FFmpeg-Documentation-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFmpeg documentation"></a></td>
<td align="center"><a href="https://ffmpeg.org/ffprobe.html"><img src="https://img.shields.io/badge/FFprobe-Media%20Inspector-007808?style=for-the-badge&logo=ffmpeg&logoColor=white" alt="FFprobe documentation"></a></td>
</tr>
<tr>
<td align="center"><a href="https://docs.docker.com/"><img src="https://img.shields.io/badge/Docker-Documentation-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker documentation"></a></td>
<td align="center"><a href="https://huggingface.co/docs/hub/spaces"><img src="https://img.shields.io/badge/Hugging%20Face-Spaces-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face Spaces documentation"></a></td>
<td align="center"><a href="https://core.telegram.org/bots/api"><img src="https://img.shields.io/badge/Telegram-Bot%20API-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram Bot API"></a></td>
</tr>
<tr>
<td align="center"><a href="https://www.imdb.com/"><img src="https://img.shields.io/badge/IMDb-Database-F5C518?style=for-the-badge&logo=imdb&logoColor=black" alt="IMDb"></a></td>
<td align="center"><a href="https://fanart.tv/api-docs/"><img src="https://img.shields.io/badge/Fanart.tv-API-8A2BE2?style=for-the-badge&logo=artstation&logoColor=white" alt="Fanart.tv API"></a></td>
<td align="center"><a href="https://github.com/"><img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a></td>
</tr>
</table>

<a id="developer"></a>
<p align="center"><img src="readme_assets/developer.svg" width="100%" alt="Developer banner"></p>

**Sadesha Hansana**  
**Sadesha Films**

Built for practical Sinhala movie and series file management with a preview-first thumbnail workflow.

## 📄 License

Add the license that matches your intended distribution before publishing this repository. If you have not selected one, keep the repository private until the licensing decision is made.
