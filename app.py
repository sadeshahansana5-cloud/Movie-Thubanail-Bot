import asyncio
import html
import io
import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
import subprocess
import unicodedata
import sqlite3
import shutil
import resource
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote

import aiohttp
from PIL import Image, ImageFont
from pyrogram import Client, filters, enums, idle
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, BotCommand

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
FANART_API_KEY = os.environ.get("FANART_API_KEY", "")
FANART_CLIENT_KEY = os.environ.get("FANART_CLIENT_KEY", "")
TVDB_API_KEY = os.environ.get("TVDB_API_KEY", "")
TVDB_PIN = os.environ.get("TVDB_PIN", "")
LOGO_PATH = os.environ.get("LOGO_PATH", str(Path(__file__).with_name("sadesha_sub_logo_ai_neon.png")))
LINE_PATH = os.environ.get("LINE_PATH", str(Path(__file__).with_name("sadesha_sub_line_neon.png")))
OVERLAY_PATHS = [x.strip() for x in os.environ.get("OVERLAY_PATHS", "").split(",") if x.strip()]
PORT = int(os.environ.get("PORT", "7860"))
MAX_FILE_MB = int(os.environ.get("MAX_FILE_MB", "2048"))
MAX_CONCURRENT_TRANSMISSIONS = int(os.environ.get("MAX_CONCURRENT_TRANSMISSIONS", "4"))
PYROGRAM_WORKERS = int(os.environ.get("PYROGRAM_WORKERS", "32"))
DB_PATH = os.environ.get("DB_PATH", "/tmp/sadesha-bot.sqlite3")
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
ALLOWED_USER_IDS = {int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()}
MAX_ACTIVE_JOBS_PER_USER = int(os.environ.get("MAX_ACTIVE_JOBS_PER_USER", "2"))
PYROGRAM_WORKDIR = os.environ.get("PYROGRAM_WORKDIR", "/tmp/sadesha-pyrogram")
Path(PYROGRAM_WORKDIR).mkdir(parents=True, exist_ok=True)

app = Client(
    "sadesha_thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN,
    workdir=PYROGRAM_WORKDIR, workers=PYROGRAM_WORKERS,
    max_concurrent_transmissions=MAX_CONCURRENT_TRANSMISSIONS,
    sleep_threshold=20,
)
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".ts", ".flv", ".wmv"}
PENDING: dict[str, dict[str, Any]] = {}
MANUAL_WAIT: dict[tuple[int, int], dict[str, Any]] = {}
CHAT_LOCKS: dict[int, asyncio.Lock] = {}
ACTIVE_JOBS: dict[str, dict[str, Any]] = {}
CANCEL_FLAGS: dict[str, asyncio.Event] = {}
USER_BATCHES: dict[tuple[int, int], dict[str, Any]] = {}
BATCH_FIX_WAIT: dict[tuple[int, int], tuple[str, int]] = {}
CHANNEL_WAIT: dict[tuple[int, int], str] = {}
PROCESSED_MEDIA: dict[str, dict[str, Any]] = {}
BOT_STARTED = time.monotonic()
DEFAULT_SETTINGS = {
    "rename_format": "title_quality",
    "thumbnail_quality": "optimized",
    "watermark": "",
    "subtitle_badge": "on",
    "send_mode": "auto",
    "progress": "on",
}


def db_init():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS settings (user_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(user_id,key))")
        db.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, quality TEXT, output_name TEXT, source TEXT, seconds REAL, file_mb REAL, created REAL)")
        db.execute("CREATE TABLE IF NOT EXISTS channels (user_id INTEGER, chat_id TEXT, title TEXT, username TEXT, added REAL, PRIMARY KEY(user_id,chat_id))")


def settings_for(user_id: int) -> dict[str, str]:
    values = dict(DEFAULT_SETTINGS)
    with sqlite3.connect(DB_PATH) as db:
        for key, value in db.execute("SELECT key,value FROM settings WHERE user_id=?", (user_id,)):
            values[key] = value
    return values


def set_setting(user_id: int, key: str, value: str):
    if key not in DEFAULT_SETTINGS:
        return
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT OR REPLACE INTO settings(user_id,key,value) VALUES(?,?,?)", (user_id, key, value))


def reset_settings(user_id: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM settings WHERE user_id=?", (user_id,))


def save_history(user_id: int, title: str, quality: str, output: str, source: str, seconds: float, file_mb: float):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO history(user_id,title,quality,output_name,source,seconds,file_mb,created) VALUES(?,?,?,?,?,?,?,?)", (user_id, title, quality, output, source, seconds, file_mb, time.time()))


def list_channels(user_id: int) -> list[dict[str, str]]:
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("SELECT chat_id,title,username FROM channels WHERE user_id=? ORDER BY title", (user_id,)).fetchall()
    return [{"chat_id": str(chat_id), "title": title or chat_id, "username": username or ""} for chat_id, title, username in rows]


def add_channel(user_id: int, chat_id: str, title: str, username: str = ""):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT OR REPLACE INTO channels(user_id,chat_id,title,username,added) VALUES(?,?,?,?,?)", (user_id, str(chat_id), title[:120], username[:120], time.time()))


def remove_channel(user_id: int, chat_id: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM channels WHERE user_id=? AND chat_id=?", (user_id, str(chat_id)))


def member_status(member: Any) -> str:
    return str(getattr(member, "status", "")).lower().split(".")[-1]


async def register_channel(owner_id: int, chat: Any) -> str:
    """Verify both administrators and save public or private channel metadata."""
    user_member = await app.get_chat_member(chat.id, owner_id)
    bot_user = await app.get_me()
    bot_member = await app.get_chat_member(chat.id, bot_user.id)
    if member_status(user_member) not in {"administrator", "creator", "owner"}:
        raise RuntimeError("ඔයා මේ channel එකේ administrator/owner කෙනෙක් නොවෙයි.")
    if member_status(bot_member) not in {"administrator", "creator", "owner"}:
        raise RuntimeError("Bot එක channel එකේ administrator කෙනෙක් කරලා නැහැ.")
    username = f"@{chat.username}" if getattr(chat, "username", None) else ""
    add_channel(owner_id, str(chat.id), chat.title or str(chat.id), username)
    return chat.title or str(chat.id)


def permitted(user_id: int) -> bool:
    return not ALLOWED_USER_IDS or user_id in ALLOWED_USER_IDS or user_id in ADMIN_IDS


def admin_only(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def prune_stale_jobs():
    now = time.monotonic()
    for token, job in list(PENDING.items()):
        created = job.get("created", now)
        if now - created > 900 and token not in ACTIVE_JOBS:
            PENDING.pop(token, None)


def user_active_count(user_id: int) -> int:
    prune_stale_jobs()
    return sum(1 for x in ACTIVE_JOBS.values() if x.get("owner") == user_id)


def system_status() -> str:
    uptime = int(time.monotonic() - BOT_STARTED)
    days, rem = divmod(uptime, 86400); hours, rem = divmod(rem, 3600); minutes, seconds = divmod(rem, 60)
    mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    disk = shutil.disk_usage("/")
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0
    ffmpeg = shutil.which("ffmpeg") is not None
    ffprobe = shutil.which("ffprobe") is not None
    return (f"Uptime: {days}d {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            f"RAM peak: {mem_mb:.1f} MB\nCPU load: {load:.2f}\n"
            f"Disk: {disk.used/1024**3:.1f}/{disk.total/1024**3:.1f} GB\n"
            f"FFmpeg: {'OK' if ffmpeg else 'Missing'} | FFprobe: {'OK' if ffprobe else 'Missing'}\n"
            f"Active jobs: {len(ACTIVE_JOBS)} | Queue: {sum(1 for x in ACTIVE_JOBS.values() if x.get('queued'))}")


db_init()


class RemoteAPIError(RuntimeError):
    pass


async def get_json(url: str, params=None, headers=None, method="GET", payload=None):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        request = session.post(url, params=params, json=payload) if method == "POST" else session.get(url, params=params)
        async with request as response:
            raw = await response.text()
            if response.status >= 400:
                raise RemoteAPIError(f"HTTP {response.status}: {raw[:220]}")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RemoteAPIError("Search service returned invalid JSON") from exc


async def get_text(url: str, params=None, headers=None) -> str:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url, params=params) as response:
            if response.status >= 400:
                raise RemoteAPIError(f"HTTP {response.status}")
            return await response.text()


async def download_bytes(url: str) -> bytes:
    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()


def clean_query(filename: str) -> str:
    """Remove channel/user/site/release noise while preserving the movie title and year."""
    name = Path(filename).stem
    name = re.sub(r"(?i)(?:www\.)?[a-z0-9-]+\.(?:com|co|net|org|tv)\s*[-_:]*", " ", name)
    # Remove only the channel prefix; never consume the actual title after Channel_.
    name = re.sub(r"(?i)@[^\s]*?telegram_channel_", " ", name)
    name = re.sub(r"(?i)@[^\s]*?telegram_", " ", name)
    name = re.sub(r"(?i)@[^\s]*?films_", " ", name)
    name = re.sub(r"(?i)@(?:[a-z0-9_]+)", " ", name)
    name = name.replace("_", " ").replace(".", " ")
    name = re.sub(r"\[[^]]*(?:cine|subz|web|dl|rip|bluray)[^]]*\]", " ", name, flags=re.I)
    name = re.sub(r"\((?=[^)]*(?:web|bluray|hdtv|x26|720p|1080p))[^)]*\)", " ", name, flags=re.I)
    name = re.sub(r"(?i)\b(?:telegram|channel|cine|subz|com|co|www)\b", " ", name)
    name = re.sub(r"(?i)\b(?:web[- ]?dl|webrip|web|bluray|brrip|hdtv|dvdrip|hdrip|x264|x265|h264|h265|hevc|10bit|2160p|1080p|720p|576p|480p|4k|8k|dual audio|multi audio|eng sub|english|telugu|tamil|hindi|malayalam|kannada)\b", " ", name)
    name = re.sub(r"(?i)\b(?:s\d{1,2}(?:e\d{1,3})?|e\d{1,3}|episode\s*\d+)\b", " ", name)
    name = re.sub(r"(?i)^[\s-]*(?:HIT|HINDI|TELUGU|TAMIL)\s+(?=[A-Za-z])", "", name)
    name = re.sub(r"[\[\]{}]+", " ", name)
    name = re.sub(r"\s*[-–—]+\s*", " ", name)
    return re.sub(r"\s+", " ", name).strip(" -_")


def output_name(original: str, title: str) -> str:
    ext = Path(original).suffix.lower() or ".mp4"
    safe = "".join(
        ch for ch in title
        if (unicodedata.category(ch).startswith(("L", "M", "N")) or ch.isspace() or ch in "()&'!-[]")
    )
    safe = re.sub(r"\s+", " ", safe).strip(" -_!.") or "renamed_media"
    return safe + ext


def extract_quality(filename: str) -> str:
    name = filename.lower().replace("_", " ").replace(".", " ")
    patterns = [
        (r"web\s*[- ]?dl", "WEB-DL"),
        (r"web\s*rip", "WEBRip"),
        (r"\bweb\b", "WEB"),
        (r"hdrip", "HDRip"),
        (r"blu\s*ray|bluray", "BluRay"),
        (r"brrip", "BRRip"),
        (r"hdtv", "HDTV"),
        (r"dvdrip", "DVDRip"),
        (r"hdcam|camrip|cam", "CAM"),
        (r"telesync|tsrip", "TS"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, name):
            return label
    return ""


def extract_resolution(filename: str) -> str:
    name = filename.lower().replace("_", " ").replace(".", " ")
    match = re.search(r"(?<!\d)(2160|1080|720|576|480)p?(?!\d)", name)
    if match:
        return f"{match.group(1)}p"
    match = re.search(r"(?<!\w)(4k|8k)(?!\w)", name)
    return match.group(1).upper() if match else ""


def parse_series_parts(filename: str) -> tuple[str, str]:
    match = re.search(r"(?i)\bS(\d{1,2})(?:E(\d{1,3}))?\b", filename)
    if not match:
        return "", ""
    return f"{int(match.group(1)):02d}", f"{int(match.group(2)):02d}" if match.group(2) else ""


def subtitle_label(filename: str) -> str:
    return "Sinhala Subtitles" if re.search(r"(?i)sinhala|sinhal|සිංහල", filename) else ""


def result_details(result: dict[str, Any], quality: str = "", resolution: str = "") -> str:
    title = f"{result['title']} {result['year']}".strip()
    return (
        f"Title: {title}\n"
        f"Quality: {quality or 'Unknown'}\n"
        f"Resolution: {resolution or 'Unknown'}"
    )


def styled_output_title(result: dict[str, Any], quality: str = "", sinhala: bool = False, format_mode: str = "title_quality") -> str:
    title = f"{result['title']} {result['year']}".strip()
    if format_mode == "quality_title" and quality:
        title = f"[{quality}] {title}"
    elif format_mode == "title_quality" and quality:
        title += f" [{quality}]"
    if sinhala:
        title += " [සිංහල උපසිරැසි සමග]"
    return title


def format_duration(seconds: int) -> str:
    hours, seconds = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def media_metadata(path: str) -> tuple[bool, int, int, int]:
    """Return (is_video, duration_seconds, width, height) for mp4/mkv/webm and similar files."""
    try:
        proc = subprocess.run([
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_entries", "format=duration:stream=codec_type,width,height",
            path,
        ], capture_output=True, text=True, timeout=45, check=True)
        data = json.loads(proc.stdout or "{}")
        streams = data.get("streams", []) or []
        video = next((x for x in streams if x.get("codec_type") == "video"), None)
        if not video:
            return False, 0, 0, 0
        duration = float((data.get("format") or {}).get("duration") or 0)
        return True, max(0, int(round(duration))), int(video.get("width") or 0), int(video.get("height") or 0)
    except Exception:
        return False, 0, 0, 0


async def imdb_lookup(query: str) -> list[dict[str, Any]]:
    url = f"https://v3.sg.media-imdb.com/suggestion/x/{quote(query)}.json"
    data = await get_json(url)
    results = []
    for item in data.get("d", []):
        imdb_id = item.get("id", "")
        if not imdb_id.startswith("tt"):
            continue
        qid = (item.get("qid") or "").lower()
        kind = "tv" if qid.startswith("tv") or "series" in qid else "movie"
        results.append({
            "kind": kind,
            "imdb_id": imdb_id,
            "title": item.get("l", query),
            "year": str(item.get("y", "")),
            "score": 100000 - int(item.get("rank", 99999)),
            "item": item,
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def iso_runtime(value: str) -> str:
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not match:
        return ""
    hours = int(match.group(1) or 0); minutes = int(match.group(2) or 0); seconds = int(match.group(3) or 0)
    return format_duration(hours * 3600 + minutes * 60 + seconds)


async def cinemeta_metadata(result: dict[str, Any]) -> dict[str, Any]:
    """No-key metadata fallback keyed by the IMDb id, including ratings and YouTube trailers."""
    try:
        kind = "series" if result.get("kind") == "tv" else "movie"
        payload = await get_json(f"https://v3-cinemeta.strem.io/meta/{kind}/{result['imdb_id']}.json")
        data = payload.get("meta") or {}
        if not data:
            return {}
        trailers = data.get("trailers") or data.get("trailerStreams") or []
        trailer_id = ""
        if trailers:
            first = trailers[0] or {}
            trailer_id = first.get("source") or first.get("ytId") or ""
        directors = data.get("director") or []
        writers = data.get("writer") or []
        return {
            "title": data.get("name") or result.get("title", ""),
            "year": str(data.get("year") or data.get("releaseInfo") or result.get("year", ""))[:4],
            "rating": str(data.get("imdbRating") or ""),
            "genres": data.get("genres") or data.get("genre") or [],
            "director": ", ".join(directors) if isinstance(directors, list) else str(directors),
            "writer": ", ".join(writers[:3]) if isinstance(writers, list) else str(writers),
            "cast": ", ".join((data.get("cast") or [])[:6]),
            "runtime": str(data.get("runtime") or ""),
            "plot": str(data.get("description") or ""),
            "country": ", ".join(data.get("country") or []) if isinstance(data.get("country"), list) else str(data.get("country") or ""),
            "awards": str(data.get("awards") or ""),
            "released": str(data.get("released") or data.get("releaseInfo") or "")[:10],
            "trailer_id": trailer_id,
            "imdb_id": result.get("imdb_id", ""),
        }
    except Exception:
        return {}


async def imdb_metadata(result: dict[str, Any]) -> dict[str, Any]:
    """Use IMDb JSON-LD when available, then fill missing fields from a no-key IMDb-id fallback."""
    meta: dict[str, Any] = {}
    try:
        raw = await get_text(
            f"https://www.imdb.com/title/{result['imdb_id']}/",
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
        )
        scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', raw, re.S | re.I)
        data = None
        for script in scripts:
            try:
                candidate = json.loads(html.unescape(script.strip()))
                data = candidate[0] if isinstance(candidate, list) else candidate
                if isinstance(data, dict) and (data.get("name") or data.get("aggregateRating")):
                    break
            except Exception:
                continue
        if isinstance(data, dict):
            people = data.get("actor") or []
            directors = data.get("director") or []
            rating = (data.get("aggregateRating") or {}).get("ratingValue")
            meta = {
            "title": data.get("name") or result.get("title", ""),
            "year": str(data.get("datePublished", ""))[:4] or result.get("year", ""),
            "rating": str(rating) if rating else "",
            "genres": data.get("genre") if isinstance(data.get("genre"), list) else ([data.get("genre")] if data.get("genre") else []),
            "director": ", ".join(x.get("name", "") for x in directors if isinstance(x, dict) and x.get("name")),
            "cast": ", ".join(x.get("name", "") for x in people[:6] if isinstance(x, dict) and x.get("name")),
            "runtime": iso_runtime(data.get("duration", "")),
            "imdb_id": result.get("imdb_id", ""),
            }
    except Exception:
        pass
    fallback = await cinemeta_metadata(result)
    for key, value in fallback.items():
        if value and not meta.get(key):
            meta[key] = value
    meta.setdefault("title", result.get("title", ""))
    meta.setdefault("year", result.get("year", ""))
    meta.setdefault("imdb_id", result.get("imdb_id", ""))
    return meta


def trailer_markup(result: dict[str, Any], meta: dict[str, Any] | None = None) -> InlineKeyboardMarkup:
    trailer_id = (meta or {}).get("trailer_id", "")
    if trailer_id:
        url = f"https://www.youtube.com/watch?v={quote(trailer_id)}"
    else:
        query = quote(f"{result.get('title', '')} {result.get('year', '')} official trailer")
        url = f"https://www.youtube.com/results?search_query={query}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Watch Trailer", url=url)]])


def media_markup(result: dict[str, Any], meta: dict[str, Any] | None = None, job_token: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("▶️ Watch Trailer", url=(trailer_markup(result, meta).inline_keyboard[0][0].url))]]
    if job_token:
        rows.append([InlineKeyboardButton("📤 Send to Channel", callback_data=f"chmenu:{job_token}")])
    return InlineKeyboardMarkup(rows)


def audio_label(filename: str, sinhala: bool) -> str:
    found = []
    for word in ("English", "Tamil", "Telugu", "Hindi", "Malayalam", "Kannada", "Korean", "Japanese"):
        if re.search(rf"(?i)\b{word}\b", filename):
            found.append(word)
    label = " / ".join(dict.fromkeys(found)) or "Unknown"
    if sinhala:
        label += " / Sinhala Subtitle"
    return label


def formatted_caption(result: dict[str, Any], meta: dict[str, Any], quality: str, resolution: str, duration: int, file_mb: float, audio: str, source: str) -> str:
    raw_title = f"{meta.get('title') or result.get('title', '')} {meta.get('year') or result.get('year', '')}".strip()
    title = html.escape(raw_title)
    rating = meta.get("rating") or "N/A"
    stars = "⭐️" * max(0, min(5, round(float(rating) / 2))) if rating != "N/A" else ""
    genres = (" | ".join(meta.get("genres") or []) or "N/A")[:100]
    director = (meta.get("director") or "N/A")[:100]
    cast = (meta.get("cast") or "N/A")[:220]
    runtime = meta.get("runtime") or format_duration(duration)
    imdb_id = meta.get('imdb_id') or result.get('imdb_id', 'N/A')
    imdb_link = f'<a href="https://www.imdb.com/title/{html.escape(imdb_id)}/">{html.escape(imdb_id)}</a>'
    plot = html.escape((meta.get("plot") or "")[:220])
    writer = html.escape((meta.get("writer") or "N/A")[:100])
    country = html.escape((meta.get("country") or "N/A")[:80])
    released = html.escape((meta.get("released") or "N/A")[:20])
    awards = html.escape((meta.get("awards") or "N/A")[:120])
    extra = f"\n📝 <b>Story:</b> {plot}" if plot else ""
    return (
        f"🎬 <b>Title:</b> {title}\n\n"
        f"⭐️ <b>IMDb Rating:</b> {html.escape(str(rating))} / 10 {stars}\n"
        f"🎭 <b>Genre:</b> {html.escape(genres)}\n"
        f"📽 <b>Director:</b> {html.escape(director)}\n"
        f"🌟 <b>Cast:</b> {html.escape(cast)}\n\n"
        f"📐 <b>Quality / Resolution:</b> {html.escape(quality or 'Unknown')} / {html.escape(resolution or 'Unknown')}\n"
        f"🔊 <b>Audio:</b> {html.escape(audio)}\n"
        f"⏱ <b>Duration:</b> {html.escape(runtime)}\n"
        f"📁 <b>File Size:</b> {file_mb:.1f} MB\n"
        f"✍️ <b>Writer:</b> {writer}\n"
        f"🌍 <b>Country:</b> {country}"
        f"\n📅 <b>Release:</b> {released}"
        f"\n🏆 <b>Awards:</b> {awards}"
        f"{extra}\n"
        f"🆔 <b>IMDb ID:</b> {imdb_link}\n\n"
        f"📥 <b>Uploaded by Sadesha Films</b>\n"
        f"<i>Artwork source: {html.escape(source)}</i>"
    )


_tvdb_token: str | None = None


async def tvdb_id_for_title(title: str) -> str | None:
    global _tvdb_token
    if not TVDB_API_KEY:
        return None
    if not _tvdb_token:
        payload = {"apikey": TVDB_API_KEY}
        if TVDB_PIN:
            payload["pin"] = TVDB_PIN
        auth = await get_json("https://api4.thetvdb.com/v4/login", method="POST", payload=payload)
        _tvdb_token = auth.get("data", {}).get("token")
    if not _tvdb_token:
        return None
    data = await get_json("https://api4.thetvdb.com/v4/search", params={"query": title, "type": "series", "limit": 10}, headers={"Authorization": f"Bearer {_tvdb_token}"})
    rows = data.get("data", []) or []
    return str(rows[0].get("tvdb_id") or rows[0].get("id")) if rows else None


async def fanart_images(result: dict[str, Any]) -> list[dict[str, Any]]:
    if not FANART_API_KEY:
        return []
    if result["kind"] == "movie":
        endpoint = f"https://webservice.fanart.tv/v3.2/movies/{result['imdb_id']}"
        keys = ["moviethumb", "moviebanner"]
    else:
        tvdb_id = await tvdb_id_for_title(result["title"])
        if not tvdb_id:
            return []
        endpoint = f"https://webservice.fanart.tv/v3.2/tv/{tvdb_id}"
        keys = ["tvthumb", "tvbanner"]
    params = {"api_key": FANART_API_KEY}
    if FANART_CLIENT_KEY:
        params["client_key"] = FANART_CLIENT_KEY
    data = await get_json(endpoint, params)
    found = []
    for key in keys:
        for image in data.get(key, []) or []:
            try:
                width, height = int(image.get("width", 0)), int(image.get("height", 0))
            except (TypeError, ValueError):
                width = height = 0
            if height and 1.65 <= width / height <= 1.85:
                item = dict(image)
                item["kind"] = key
                found.append(item)
    return sorted(found, key=lambda x: int(x.get("likes", 0) or 0), reverse=True)


async def yandex_images(result: dict[str, Any]) -> list[dict[str, Any]]:
    query = f"{result['title']} {result['year']} official movie banner 16:9".strip()
    raw = html.unescape(await get_text("https://yandex.com/images/search", params={"text": query, "family": "yes"}, headers={"User-Agent": "Mozilla/5.0"}))
    found = []
    seen = set()
    for url in re.findall(r'origUrl":"(https?://[^"\\]+)', raw):
        url = url.replace("\\/", "/")
        if url not in seen:
            seen.add(url)
            found.append({"url": url, "kind": "public-image-search"})
        if len(found) >= 25:
            break
    return found


async def choose_landscape(images: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen = []
    for item in images[:20]:
        try:
            raw = await download_bytes(item["url"])
            with Image.open(io.BytesIO(raw)) as image:
                width, height = image.size
            if height and 1.65 <= width / height <= 1.85:
                item = dict(item)
                item.update(width=width, height=height)
                chosen.append(item)
                if len(chosen) >= 5:
                    break
        except Exception:
            continue
    return chosen


async def artwork_for(result: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        images = await fanart_images(result)
    except Exception:
        images = []
    if images:
        return images
    try:
        return await choose_landscape(await yandex_images(result))
    except Exception:
        return []


async def search_art(query: str):
    results = await imdb_lookup(query)
    if not results:
        return None, []
    for result in results[:8]:
        images = await artwork_for(result)
        if images:
            return result, images
    return results[0], []


def display_name(result: dict[str, Any]) -> str:
    return f"{result['title']} {result['year']} ({'Series' if result['kind'] == 'tv' else 'Movie'})".strip()


def make_telegram_thumb(data: bytes, watermark: str = "", quality_mode: str = "optimized", logo_path: str = LOGO_PATH) -> io.BytesIO:
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    image.thumbnail((320, 320), Image.Resampling.LANCZOS)
    logo_added = False
    overlay_paths = [logo_path] + OVERLAY_PATHS
    for overlay_path in overlay_paths:
        if not overlay_path or not Path(overlay_path).exists():
            continue
        try:
            logo = Image.open(overlay_path).convert("RGBA")
            max_width = max(100, int(image.width * 0.46))
            ratio = max_width / logo.width
            logo = logo.resize((max_width, max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)
            x = max(4, image.width - logo.width - 6)
            y = 3
            image.alpha_composite(logo, (x, y))
            if LINE_PATH and Path(LINE_PATH).exists():
                line_art = Image.open(LINE_PATH).convert("RGBA")
                line_width = max(90, int(image.width * 0.40))
                line_ratio = line_width / line_art.width
                line_art = line_art.resize((line_width, max(1, int(line_art.height * line_ratio))), Image.Resampling.LANCZOS)
                line_x = max(4, image.width - line_art.width - 6)
                line_y = min(image.height - line_art.height - 3, y + logo.height - 8)
                image.alpha_composite(line_art, (line_x, line_y))
            logo_added = True
            break
        except Exception:
            logging.exception("logo overlay failed")
    if watermark and not logo_added:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        font = None
        for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
            if Path(candidate).exists():
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype(candidate, max(10, image.width // 22))
                    break
                except Exception:
                    pass
        font = font or ImageFont.load_default()
        box = draw.textbbox((0, 0), watermark, font=font)
        x, y = image.width - (box[2] - box[0]) - 8, image.height - (box[3] - box[1]) - 8
        draw.rectangle((x - 4, y - 3, image.width - 3, image.height - 3), fill=(0, 0, 0, 150))
        draw.text((x, y), watermark, fill="white", font=font)
    output = io.BytesIO()
    quality_list = {"low": (58, 50, 42), "medium": (75, 65, 55), "high": (95, 88, 78), "optimized": (88, 78, 68)}.get(quality_mode, (88, 78, 68))
    for quality in quality_list:
        output.seek(0)
        output.truncate(0)
        image.convert("RGB").save(output, "JPEG", quality=quality, optimize=True, progressive=True)
        if output.tell() < 190_000:
            break
    output.seek(0)
    output.name = "thumbnail.jpg"
    return output


def progress_text(phase: str, current: int, total: int, started: float) -> str:
    elapsed = max(time.monotonic() - started, 0.1)
    percent = (current / total * 100) if total else 0
    speed = current / elapsed
    eta = ((total - current) / speed) if speed and total else 0
    filled = int(percent // 5)
    bar = "█" * filled + "░" * (20 - filled)
    def size(n):
        return f"{n / 1024 / 1024:.1f} MB"
    return f"{phase}\n[{bar}] {percent:.1f}%\n{size(current)} / {size(total)}\nSpeed: {size(speed)}/s  •  ETA: {int(eta)}s"


async def safe_edit(message: Message, text: str):
    try:
        await message.edit_text(text)
    except FloodWait as wait:
        await asyncio.sleep(min(wait.value + 1, 8))
    except Exception:
        pass


def make_progress_callback(status: Message, phase: str):
    started = time.monotonic()
    last = [0.0]
    async def progress(current: int, total: int, *_):
        now = time.monotonic()
        if now - last[0] >= 5.0 or (total and current >= total):
            last[0] = now
            await safe_edit(status, progress_text(phase, current, total, started))
    return progress


async def animate(status: Message, stop: asyncio.Event, text: str):
    dots = 0
    while not stop.is_set():
        await safe_edit(status, text + "." * (dots % 4))
        dots += 1
        try:
            await asyncio.wait_for(stop.wait(), timeout=3.5)
        except asyncio.TimeoutError:
            pass


async def send_art(message: Message, result: dict[str, Any], images: list[dict[str, Any]]):
    status = await message.reply_text("Downloading")
    stop = asyncio.Event()
    task = asyncio.create_task(animate(status, stop, "Downloading"))
    try:
        data = await download_bytes(images[0]["url"])
        artwork = io.BytesIO(data)
        artwork.name = "thumbnail.jpg"
        await message.reply_photo(artwork, caption=f"{display_name(result)}\nSource: {images[0].get('kind', 'image')}")
    finally:
        stop.set()
        await task
        await status.delete()


async def show_preview(callback, token: str, result: dict[str, Any], image: dict[str, Any], media_info: dict[str, Any] | None = None):
    data = await download_bytes(image["url"])
    preview = io.BytesIO(data)
    preview.name = "thumbnail.jpg"
    quality = (PENDING.get(token) or {}).get("quality", "")
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Done - normal name", callback_data=f"done:{token}:plain")],
        [InlineKeyboardButton("Done + Sinhala Subtitles", callback_data=f"done:{token}:sinhala")],
        [InlineKeyboardButton("⛔ Cancel", callback_data=f"cancel:{token}")],
    ])
    gallery = (PENDING.get(token) or {}).get("images", [])
    if len(gallery) > 1:
        current = (PENDING.get(token) or {}).get("image_index", 0)
        buttons.inline_keyboard.insert(0, [InlineKeyboardButton(f"Next thumbnail ({current + 1}/{len(gallery)})", callback_data=f"img:{token}:{(current + 1) % len(gallery)}")])
    caption = f"{display_name(result)}\nQuality: {quality or 'Unknown'}\n\nමේ photo එක හරි නම් option එකක් තෝරන්න."
    sent = await callback.message.reply_photo(preview, caption=caption, reply_markup=buttons)
    if media_info:
        PENDING[token]["preview_message_id"] = sent.id


async def process_media(source: Message, result: dict[str, Any], image: dict[str, Any], status: Message, quality: str = "", resolution: str = "", sinhala: bool = False, settings_override: dict[str, str] | None = None, job_token: str | None = None):
    started_at = time.monotonic()
    user_id = source.from_user.id if source.from_user else 0
    settings = settings_override or settings_for(user_id)
    sinhala = sinhala and settings.get("subtitle_badge", "on") == "on"
    original = ((source.video or source.document).file_name if (source.video or source.document) else "media.mp4") or "media.mp4"
    if (source.video or source.document).file_size and (source.video or source.document).file_size > MAX_FILE_MB * 1024 * 1024:
        await safe_edit(status, f"File එක {MAX_FILE_MB} MB limit එකට වඩා විශාලයි.")
        return
    try:
        artwork_data = await download_bytes(image["url"])
        thumb = make_telegram_thumb(artwork_data, settings.get("watermark", ""), settings.get("thumbnail_quality", "optimized"))
        with tempfile.TemporaryDirectory() as tmp:
            local_path = os.path.join(tmp, original)
            download_progress = make_progress_callback(status, "Downloading file") if settings.get("progress", "on") == "on" else None
            path = await source.download(file_name=local_path, progress=download_progress)
            is_video, duration, width, height = media_metadata(path)
            renamed = output_name(original, styled_output_title(result, quality, sinhala, settings.get("rename_format", "title_quality")))
            renamed_path = os.path.join(tmp, renamed)
            os.replace(path, renamed_path)
            upload_progress = make_progress_callback(status, "Uploading with thumbnail") if settings.get("progress", "on") == "on" else None
            file_mb = os.path.getsize(renamed_path) / 1024 / 1024
            season, episode = parse_series_parts(original)
            series_details = f"\nSeason: {season}" + (f" | Episode: {episode}" if episode else "") if season else ""
            meta = await imdb_metadata(result)
            caption = formatted_caption(
                result, meta, quality, resolution, duration, file_mb,
                audio_label(original, sinhala), image.get("kind", "image"),
            )
            if len(caption) > 1020:
                safe_title = html.escape(f"{meta.get('title') or result.get('title', '')} {meta.get('year') or result.get('year', '')}".strip())
                safe_id = html.escape(meta.get("imdb_id") or result.get("imdb_id", "N/A"))
                caption = (
                    f"🎬 <b>Title:</b> {safe_title}\n\n"
                    f"⭐️ <b>IMDb Rating:</b> {html.escape(str(meta.get('rating') or 'N/A'))} / 10\n"
                    f"📐 <b>Quality / Resolution:</b> {html.escape(quality or 'Unknown')} / {html.escape(resolution or 'Unknown')}\n"
                    f"🔊 <b>Audio:</b> {html.escape(audio_label(original, sinhala))}\n"
                    f"⏱ <b>Duration:</b> {html.escape(format_duration(duration))}\n"
                    f"📁 <b>File Size:</b> {file_mb:.1f} MB\n"
                    f"🆔 <b>IMDb ID:</b> <a href=\"https://www.imdb.com/title/{safe_id}/\">{safe_id}</a>\n\n"
                    "📥 <b>Uploaded by Sadesha Films</b>"
                )
            send_mode = settings.get("send_mode", "auto")
            if is_video and send_mode != "document":
                sent_media = await app.send_video(
                    source.chat.id, renamed_path, thumb=thumb, caption=caption,
                    duration=duration, width=width, height=height,
                    supports_streaming=True, progress=upload_progress,
                    parse_mode=enums.ParseMode.HTML, reply_markup=media_markup(result, meta, job_token),
                    reply_to_message_id=source.id,
                )
            else:
                sent_media = await app.send_document(
                    source.chat.id, renamed_path, thumb=thumb, caption=caption,
                    file_name=renamed, progress=upload_progress,
                    parse_mode=enums.ParseMode.HTML, reply_markup=media_markup(result, meta, job_token),
                    reply_to_message_id=source.id,
                )
            if job_token and sent_media:
                PROCESSED_MEDIA[job_token] = {
                    "owner": user_id, "chat_id": source.chat.id, "message_id": sent_media.id,
                    "title": f"{result.get('title', '')} {result.get('year', '')}".strip(),
                }
        try:
            await source.reply_text(
                "『 ✅ JOB COMPLETED 』\n"
                f"{result_details(result, quality, resolution)}\n"
                f"Duration: {format_duration(duration)}\n"
                f"File: {file_mb:.1f} MB\n"
                f"Thumbnail: {image.get('kind', 'image')}\n"
                f"Output: {renamed}\n"
                f"Total time: {format_duration(int(time.monotonic() - started_at))}"
            )
        except Exception:
            logging.exception("completion report could not be sent")
        await safe_edit(status, f"Done ✓\nRenamed: {renamed}")
        save_history(user_id, f"{result['title']} {result['year']}".strip(), quality, renamed, image.get("kind", "image"), time.monotonic() - started_at, file_mb)
        await asyncio.sleep(2)
        try:
            await status.delete()
        except Exception:
            pass
    except Exception as exc:
        logging.exception("media processing failed")
        await safe_edit(status, f"File processing error: {exc}")


async def handle_media_message(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not permitted(user_id):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    current_for_user = user_active_count(user_id)
    if current_for_user >= MAX_ACTIVE_JOBS_PER_USER:
        await message.reply_text(f"ඔයාගේ active job limit එක ({MAX_ACTIVE_JOBS_PER_USER}) පිරී ඇත. පසුව retry කරන්න.")
        return
    media = message.video or message.document
    original = (media.file_name if media else "") or "media.mp4"
    query = clean_query(original)
    quality = extract_quality(original)
    resolution = extract_resolution(original)
    media_info = {"chat_id": message.chat.id, "message_id": message.id, "original": original, "quality": quality, "resolution": resolution}
    if not query:
        MANUAL_WAIT[(message.chat.id, message.from_user.id if message.from_user else 0)] = {**media_info, "created": time.monotonic()}
        await message.reply_text("මේ file එකේ නමෙන් title එක හඳුනාගන්න බැහැ. Movie/Series නමක් reply එකක් ලෙස එවන්න.")
        return
    status = await message.reply_text(f"Title: {query}\nArtwork සොයමින්")
    try:
        result, images = await search_art(query)
        if not result or not images:
            MANUAL_WAIT[(message.chat.id, message.from_user.id if message.from_user else 0)] = {**media_info, "created": time.monotonic()}
            await safe_edit(status, f"{query} සඳහා artwork හමු වුණේ නැහැ. Movie/Series නමක් reply එකක් ලෙස එවන්න.")
            return
        token = uuid.uuid4().hex[:10]
        PENDING[token] = {
            "owner": message.from_user.id if message.from_user else 0,
            "results": [result], "media": media_info, "result": result,
            "image": images[0], "quality": quality, "resolution": resolution, "status_message_id": status.id,
            "created": time.monotonic(),
        }
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Done - normal name", callback_data=f"done:{token}:plain")],
            [InlineKeyboardButton("Done + Sinhala Subtitles", callback_data=f"done:{token}:sinhala")],
            [InlineKeyboardButton("⛔ Cancel", callback_data=f"cancel:{token}")],
        ])
        await status.edit_text(
            result_details(result, quality, resolution) +
            "\n\nThumbnail ready. Choose how to name the file:",
            reply_markup=buttons,
        )
    except Exception as exc:
        logging.exception("automatic media handler failed")
        await safe_edit(status, f"File එක process කරන්න බැරි වුණා: {exc}")


async def run_media_serially(message: Message):
    lock = CHAT_LOCKS.setdefault(message.chat.id, asyncio.Lock())
    async with lock:
        await handle_media_message(message)


def settings_markup(user_id: int) -> InlineKeyboardMarkup:
    s = settings_for(user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Rename: {s['rename_format']}", callback_data="cfg:rename")],
        [InlineKeyboardButton(f"Thumbnail: {s['thumbnail_quality']}", callback_data="cfg:thumb")],
        [InlineKeyboardButton(f"Watermark: {s['watermark'] or 'OFF'}", callback_data="cfg:watermark")],
        [InlineKeyboardButton(f"Sinhala badge: {s['subtitle_badge']}", callback_data="cfg:badge")],
        [InlineKeyboardButton(f"Send mode: {s['send_mode']}", callback_data="cfg:send")],
        [InlineKeyboardButton(f"Progress: {s['progress']}", callback_data="cfg:progress")],
        [InlineKeyboardButton("Reset all defaults", callback_data="cfg:reset")],
    ])


async def settings_page(message: Message):
    user_id = message.from_user.id if message.from_user else 0
    await message.reply_text("『 ⚙️ SADESHA FILMS SETTINGS 』\nChoose a setting:", reply_markup=settings_markup(user_id))


@app.on_message(filters.command("settings"))
async def settings_command(_, message: Message):
    if not permitted(message.from_user.id if message.from_user else 0):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    await settings_page(message)


@app.on_message(filters.command("watermark"))
async def watermark_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    value = " ".join(message.command[1:]).strip()
    set_setting(user_id, "watermark", "" if value.lower() in {"off", "none", "disable"} else value[:40])
    await message.reply_text("Watermark updated.", reply_markup=settings_markup(user_id))


@app.on_callback_query(filters.regex(r"^cfg:"))
async def settings_callback(_, callback):
    user_id = callback.from_user.id
    action = callback.data.split(":", 1)[1]
    if action == "back":
        await callback.answer()
        await callback.message.edit_text("『 ⚙️ SADESHA FILMS SETTINGS 』\nChoose a setting:", reply_markup=settings_markup(user_id))
        return
    if action == "reset":
        reset_settings(user_id)
        await callback.answer("Defaults restored")
        await callback.message.edit_text("Settings reset to defaults.", reply_markup=settings_markup(user_id))
        return
    options = {
        "rename": [("Title [Quality]", "rename_format", "title_quality"), ("[Quality] Title", "rename_format", "quality_title"), ("Title only", "rename_format", "title_only")],
        "thumb": [("Optimized", "thumbnail_quality", "optimized"), ("Low", "thumbnail_quality", "low"), ("Medium", "thumbnail_quality", "medium"), ("High", "thumbnail_quality", "high")],
        "badge": [("Badge ON", "subtitle_badge", "on"), ("Badge OFF", "subtitle_badge", "off")],
        "send": [("Auto detect", "send_mode", "auto"), ("Always video", "send_mode", "video"), ("Always document", "send_mode", "document")],
        "progress": [("Progress ON", "progress", "on"), ("Progress OFF", "progress", "off")],
        "watermark": [("SADESHA FILMS", "watermark", "SADESHA FILMS"), ("Sadesha Films", "watermark", "Sadesha Films"), ("Turn OFF", "watermark", "")],
    }
    if action not in options:
        await callback.answer("Use /watermark text to set a custom watermark")
        return
    buttons = [[InlineKeyboardButton(label, callback_data=f"set:{key}:{value}")] for label, key, value in options[action]]
    buttons.append([InlineKeyboardButton("Back", callback_data="cfg:back")])
    await callback.answer()
    await callback.message.edit_text("Select an option:", reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex(r"^set:"))
async def settings_set_callback(_, callback):
    _, key, value = callback.data.split(":", 2)
    set_setting(callback.from_user.id, key, value)
    await callback.answer("Saved")
    await callback.message.edit_text("『 ⚙️ SETTINGS 』\nSaved successfully.", reply_markup=settings_markup(callback.from_user.id))


@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text("『 🎬 SADESHA FILMS BOT 🎬 』\n\n/start  /settings  /channels  /thumb  /search  /status  /queue  /history\n\nFile එකක් upload කරන්න. Title, IMDb metadata, quality, resolution සහ thumbnail automatically handle කරයි.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Settings", callback_data="cfg:back")], [InlineKeyboardButton("📣 Channels", callback_data="chpanel")]]))


@app.on_message(filters.command("thumb"))
async def thumb(_, message: Message):
    if not permitted(message.from_user.id if message.from_user else 0):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    query = " ".join(message.command[1:]).strip()
    if not query:
        await message.reply_text("භාවිතය: /thumb Moana 2026")
        return
    await show_search_buttons(message, query)


async def show_search_buttons(message: Message, query: str, media_info: dict[str, Any] | None = None):
    status = await message.reply_text("Searching")
    stop = asyncio.Event()
    task = asyncio.create_task(animate(status, stop, "Searching"))
    try:
        results = await imdb_lookup(query)
        if not results:
            await safe_edit(status, "Movie/Series නමක් reply එකක් ලෙස එවන්න.")
            return
        token = uuid.uuid4().hex[:10]
        PENDING[token] = {"owner": message.from_user.id if message.from_user else 0, "results": results[:30], "media": media_info, "created": time.monotonic()}
        await status.edit_text("නිවැරදි result එක තෝරන්න:", reply_markup=search_markup(token, 0))
    except Exception as exc:
        logging.exception("search buttons failed")
        await safe_edit(status, f"Search error: {exc}")
    finally:
        stop.set()
        await task


def search_markup(token: str, page: int) -> InlineKeyboardMarkup:
    results = PENDING[token]["results"]
    start = page * 5
    rows = []
    for index, result in enumerate(results[start:start + 5], start):
        label = f"{result['title']} {result['year']} - {'Series' if result['kind'] == 'tv' else 'Movie'}"
        rows.append([InlineKeyboardButton(label[:60], callback_data=f"pick:{token}:{index}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page:{token}:{page - 1}"))
    if start + 5 < len(results):
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{token}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(f"Page {page + 1}/{max(1, (len(results) + 4) // 5)}", callback_data="noop")])
    return InlineKeyboardMarkup(rows)


@app.on_callback_query(filters.regex(r"^page:"))
async def search_page(_, callback):
    _, token, page = callback.data.split(":")
    pending = PENDING.get(token)
    if not pending or (pending.get("owner") and pending["owner"] != callback.from_user.id):
        await callback.answer("Search expired or not yours.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=search_markup(token, int(page)))


@app.on_callback_query(filters.regex(r"^noop$"))
async def noop_callback(_, callback):
    await callback.answer()


@app.on_callback_query(filters.regex(r"^pick:"))
async def pick(_, callback):
    try:
        _, token, index = callback.data.split(":")
        pending = PENDING.get(token)
        if not pending:
            await callback.answer("මේ selection එක expire වෙලා.", show_alert=True)
            return
        if pending["owner"] and callback.from_user.id != pending["owner"]:
            await callback.answer("මේ search එක ඔයාගේ එකක් නෙවෙයි.", show_alert=True)
            return
        result = pending["results"][int(index)]
        pending["result"] = result
        pending["quality"] = (pending.get("media") or {}).get("quality", "")
        pending["resolution"] = (pending.get("media") or {}).get("resolution", "")
        await callback.answer("තෝරාගත්තා")
        await callback.message.edit_text(f"{display_name(result)}\nArtwork සොයමින්")
        images = await artwork_for(result)
        if not images:
            await callback.message.edit_text("මේ title එකට photo එකක් හමු වුණේ නැහැ. වෙන result එකක් තෝරන්න.")
            return
        pending["image"] = images[0]
        pending["images"] = images
        pending["image_index"] = 0
        if pending.get("media"):
            await show_preview(callback, token, result, images[0], pending["media"])
        else:
            await send_art(callback.message, result, images)
    except Exception as exc:
        logging.exception("button selection failed")
        await callback.answer("Search error", show_alert=True)


@app.on_callback_query(filters.regex(r"^img:"))
async def image_gallery_callback(_, callback):
    _, token, index = callback.data.split(":")
    pending = PENDING.get(token)
    if not pending or pending.get("owner") != callback.from_user.id or not pending.get("images"):
        await callback.answer("Gallery expired or not yours.", show_alert=True)
        return
    index = int(index) % len(pending["images"])
    pending["image_index"] = index
    pending["image"] = pending["images"][index]
    await callback.answer("Thumbnail changed")
    await callback.message.delete()
    await show_preview(callback, token, pending["result"], pending["image"], pending.get("media"))


@app.on_callback_query(filters.regex(r"^done:"))
async def done(_, callback):
    _, token, mode = callback.data.split(":", 2)
    pending = PENDING.get(token)
    if not pending or not pending.get("media") or not pending.get("result") or not pending.get("image"):
        await callback.answer("මේ job එක expire වෙලා.", show_alert=True)
        return
    if pending["owner"] and callback.from_user.id != pending["owner"]:
        await callback.answer("මේ job එක ඔයාගේ එකක් නෙවෙයි.", show_alert=True)
        return
    await callback.answer("File processing ආරම්භ කළා")
    await callback.message.edit_reply_markup(reply_markup=None)
    media = pending["media"]
    pending["task"] = asyncio.current_task()
    ACTIVE_JOBS[token] = pending
    CANCEL_FLAGS[token] = asyncio.Event()
    try:
        source = await app.get_messages(media["chat_id"], media["message_id"])
        status = await callback.message.reply_text("Preparing file")
        await process_media(
            source, pending["result"], pending["image"], status,
            quality=pending.get("quality", ""), resolution=pending.get("resolution", ""), sinhala=(mode == "sinhala"), job_token=token,
        )
        media_info = pending.get("media") or {}
        if media_info.get("batch_fix"):
            batch_key = (media_info.get("chat_id"), pending.get("owner", 0))
            batch = USER_BATCHES.get(batch_key)
            failed_index = media_info.get("failed_index")
            if batch and isinstance(failed_index, int) and failed_index < len(batch.get("failed", [])):
                batch["failed"].pop(failed_index)
                await callback.message.reply_text("✅ Failed item fixed and processed successfully.")
    except Exception as exc:
        logging.exception("done processing failed")
        await callback.message.reply_text(f"File processing error: {exc}")
    finally:
        PENDING.pop(token, None)
        ACTIVE_JOBS.pop(token, None)
        CANCEL_FLAGS.pop(token, None)


def channels_markup(user_id: int, token: str = "panel") -> InlineKeyboardMarkup:
    rows = []
    for index, channel in enumerate(list_channels(user_id)):
        label = f"📤 {channel['title']}"[:55]
        if token != "panel":
            rows.append([InlineKeyboardButton(label, callback_data=f"chsend:{token}:{index}")])
        else:
            rows.append([InlineKeyboardButton(label, callback_data="noop")])
        rows.append([InlineKeyboardButton(f"🗑 Remove {channel['title']}"[:55], callback_data=f"chremove:{token}:{index}")])
    rows.append([InlineKeyboardButton("➕ Add Channel", callback_data=f"chadd:{token}")])
    if token != "panel":
        rows.append([InlineKeyboardButton("⬅️ Back", callback_data=f"chback:{token}")])
    return InlineKeyboardMarkup(rows)


def channels_text(user_id: int, token: str = "panel") -> str:
    rows = list_channels(user_id)
    text = "『 📣 CHANNEL SEND 』\n"
    text += "Saved channels:\n" if rows else "No channels saved yet.\n"
    for i, channel in enumerate(rows, 1):
        text += f"{i}. {channel['title']} {channel['username']}\n"
    if token != "panel":
        text += "\nSend the processed file to one of these channels:"
    else:
        text += "\nAdd a channel only after you are an admin and the bot is an administrator."
    return text


@app.on_message(filters.command("channels"))
async def channels_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not permitted(user_id):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    await message.reply_text(channels_text(user_id), reply_markup=channels_markup(user_id))


@app.on_callback_query(filters.regex(r"^chmenu:"))
async def channel_menu_callback(_, callback):
    token = callback.data.split(":", 1)[1]
    media = PROCESSED_MEDIA.get(token)
    if not media or media.get("owner") != callback.from_user.id:
        await callback.answer("This processed post expired or is not yours.", show_alert=True)
        return
    await callback.answer()
    await callback.message.reply_text(channels_text(callback.from_user.id, token), reply_markup=channels_markup(callback.from_user.id, token))


@app.on_callback_query(filters.regex(r"^chpanel$"))
async def channel_panel_callback(_, callback):
    await callback.answer()
    await callback.message.reply_text(channels_text(callback.from_user.id), reply_markup=channels_markup(callback.from_user.id))


@app.on_callback_query(filters.regex(r"^chadd:"))
async def channel_add_callback(_, callback):
    token = callback.data.split(":", 1)[1]
    if token != "panel":
        media = PROCESSED_MEDIA.get(token)
        if not media or media.get("owner") != callback.from_user.id:
            await callback.answer("This job expired or is not yours.", show_alert=True); return
    CHANNEL_WAIT[(callback.message.chat.id, callback.from_user.id)] = token
    await callback.answer()
    await callback.message.reply_text("Add channel: send its @username or numeric -100... channel ID. You must be a channel admin and the bot must already be an administrator.")


@app.on_callback_query(filters.regex(r"^chremove:"))
async def channel_remove_callback(_, callback):
    _, token, index = callback.data.split(":")
    channels = list_channels(callback.from_user.id)
    if int(index) >= len(channels):
        await callback.answer("Channel not found.", show_alert=True); return
    remove_channel(callback.from_user.id, channels[int(index)]["chat_id"])
    await callback.answer("Channel removed")
    await callback.message.edit_text(channels_text(callback.from_user.id, token), reply_markup=channels_markup(callback.from_user.id, token))


@app.on_callback_query(filters.regex(r"^chsend:"))
async def channel_send_callback(_, callback):
    _, token, index = callback.data.split(":")
    media = PROCESSED_MEDIA.get(token)
    channels = list_channels(callback.from_user.id)
    if not media or media.get("owner") != callback.from_user.id or int(index) >= len(channels):
        await callback.answer("Processed file or channel not found.", show_alert=True); return
    channel = channels[int(index)]
    try:
        await app.copy_message(channel["chat_id"], media["chat_id"], media["message_id"])
        await callback.answer(f"Sent to {channel['title']}")
        await callback.message.reply_text(f"✅ Sent to channel: {channel['title']}")
    except Exception as exc:
        logging.exception("channel copy failed")
        await callback.answer("Channel send failed", show_alert=True)
        await callback.message.reply_text(f"Channel send failed: {exc}")


@app.on_callback_query(filters.regex(r"^chback:"))
async def channel_back_callback(_, callback):
    token = callback.data.split(":", 1)[1]
    media = PROCESSED_MEDIA.get(token)
    if media and media.get("owner") == callback.from_user.id:
        await callback.answer()
        await callback.message.edit_text(channels_text(callback.from_user.id, token), reply_markup=channels_markup(callback.from_user.id, token))
    else:
        await callback.answer("This menu expired.", show_alert=True)


@app.on_message(filters.command("search"))
async def search(_, message: Message):
    if not permitted(message.from_user.id if message.from_user else 0):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    query = " ".join(message.command[1:]).strip()
    if not query:
        await message.reply_text("භාවිතය: /search Stranger Things")
        return
    try:
        results = await imdb_lookup(query)
        if not results:
            await message.reply_text("IMDb result එකක් හමු වුණේ නැහැ.")
            return
        await message.reply_text("\n".join(f"{i}. {display_name(x)}" for i, x in enumerate(results[:8], 1)))
    except Exception as exc:
        await message.reply_text(f"Search error: {exc}")


@app.on_message(filters.command("status"))
async def status(_, message: Message):
    try:
        test = await imdb_lookup("Moana 2026")
        imdb_state = f"OK ({test[0]['imdb_id']})" if test else "OK but no result"
    except Exception as exc:
        imdb_state = f"ERROR: {exc}"
    await message.reply_text(
        "『 📊 SERVER STATUS 』\n"
        f"{system_status()}\n"
        f"IMDb Search: {imdb_state}\n"
        f"Fanart: {'Configured' if FANART_API_KEY else 'Fallback mode'}\n"
        f"TVDB: {'Configured' if TVDB_API_KEY else 'Optional / not set'}\n"
        f"Telegram: Connected via Pyrogram\n"
        f"Allowed users: {'All' if not ALLOWED_USER_IDS else len(ALLOWED_USER_IDS)}"
    )


@app.on_message(filters.command("queue"))
async def queue_command(_, message: Message):
    rows = [f"{i}. {x.get('title','job')} — {'queued' if x.get('queued') else 'active'}" for i, x in enumerate(ACTIVE_JOBS.values(), 1)]
    await message.reply_text("『 📥 QUEUE 』\n" + ("\n".join(rows) if rows else "Queue is empty."))


@app.on_message(filters.command("history"))
async def history_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute("SELECT title,quality,output_name,file_mb FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall()
    text = "\n".join(f"{i}. {r[0]} [{r[1] or 'Unknown'}] — {r[2]} ({r[3]:.1f} MB)" for i, r in enumerate(rows, 1))
    await message.reply_text("『 🗂 HISTORY 』\n" + (text or "No completed jobs yet."))


@app.on_message(filters.command("cancel"))
async def cancel_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    found = []
    for token, job in list(PENDING.items()) + list(ACTIVE_JOBS.items()):
        if job.get("owner") == user_id:
            flag = CANCEL_FLAGS.setdefault(token, asyncio.Event()); flag.set()
            task = job.get("task")
            if task and not task.done(): task.cancel()
            PENDING.pop(token, None); ACTIVE_JOBS.pop(token, None)
            found.append(token)
    await message.reply_text(f"⛔ Cancelled {len(found)} of your job(s)." if found else "ඔයාගේ active job එකක් නැහැ.")


@app.on_message(filters.command("admin"))
async def admin_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not admin_only(user_id):
        await message.reply_text("Admin only command.")
        return
    await message.reply_text(f"『 🔐 ADMIN 』\nAdmins: {len(ADMIN_IDS)}\nAllowed users: {len(ALLOWED_USER_IDS) or 'All'}\nActive jobs: {len(ACTIVE_JOBS)}")


@app.on_message(filters.command("users"))
async def users_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not admin_only(user_id):
        await message.reply_text("Admin only command.")
        return
    await message.reply_text(f"Admins: {', '.join(map(str, sorted(ADMIN_IDS))) or 'none'}\nAllowed: {', '.join(map(str, sorted(ALLOWED_USER_IDS))) or 'all users'}\nLimit per user: {MAX_ACTIVE_JOBS_PER_USER}")


@app.on_message(filters.command("clearqueue"))
async def clear_queue_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not admin_only(user_id):
        await message.reply_text("Admin only command.")
        return
    for token, job in list(PENDING.items()):
        if job.get("media"):
            PENDING.pop(token, None)
    await message.reply_text("Queue cleared.")


async def send_batch_summary(batch: dict[str, Any], status: Message):
    total = len(batch.get("items", [])) + len(batch.get("done", [])) + len(batch.get("failed", []))
    done_count = len(batch.get("done", []))
    failed = batch.get("failed", [])
    text = f"『 📦 BATCH COMPLETE 』\nProcessed: {done_count}/{total}\nFailed: {len(failed)}"
    rows = []
    for i, item in enumerate(failed):
        label = f"Fix {i + 1}: {item.get('original', 'unknown')[:45]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"batchfix:{batch['id']}:{i}")])
    if failed:
        text += "\n\nThumbnail/IMDb failed files:"
    await safe_edit(status, text)
    if rows:
        await status.edit_reply_markup(reply_markup=InlineKeyboardMarkup(rows))


async def run_batch(batch: dict[str, Any], command_message: Message):
    batch["done"] = []
    batch["failed"] = []
    total = len(batch["items"])
    status = await command_message.reply_text(f"Batch starting: 0/{total}")
    for index, item in enumerate(list(batch["items"]), 1):
        if batch.get("cancelled"):
            break
        try:
            source = await app.get_messages(item["chat_id"], item["message_id"])
            original = item["original"]
            query = clean_query(original)
            quality = extract_quality(original)
            resolution = extract_resolution(original)
            await safe_edit(status, f"Processing {index}/{total}\nRemaining: {total - index}\nTitle: {query or 'unknown'}")
            result, images = await search_art(query) if query else (None, [])
            if not result or not images:
                batch["failed"].append({**item, "reason": "Missing IMDb or 16:9 thumbnail"})
            else:
                token = f"batch-{batch['id']}-{index}"
                ACTIVE_JOBS[token] = {"owner": batch["owner"], "title": result.get("title"), "queued": False}
                try:
                    process_status = await command_message.reply_text(f"Processing {index}/{total}: downloading/uploading")
                    await process_media(source, result, images[0], process_status, quality, resolution, batch.get("sinhala", False), settings_override={**settings_for(batch["owner"]), "subtitle_badge": "on" if batch.get("sinhala") else "off"}, job_token=token)
                finally:
                    ACTIVE_JOBS.pop(token, None)
                batch["done"].append({**item, "title": result.get("title")})
        except Exception as exc:
            logging.exception("batch item failed")
            batch["failed"].append({**item, "reason": str(exc)[:120]})
        if index < total and not batch.get("cancelled"):
            await safe_edit(status, f"Waiting 20 seconds…\nCompleted: {index}/{total}\nNext: {index + 1}/{total}")
            await asyncio.sleep(20)
    batch["items"].clear()
    batch["running"] = False
    await send_batch_summary(batch, status)


@app.on_message(filters.command("batch"))
async def batch_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not permitted(user_id):
        await message.reply_text("ඔයාට මේ bot එක භාවිතා කිරීමට අවසර නැහැ.")
        return
    key = (message.chat.id, user_id)
    old = USER_BATCHES.get(key)
    if old and (old.get("collecting") or old.get("running")):
        await message.reply_text("ඔයාගේ batch එක දැනටමත් active. Files add කරලා /batchdone කරන්න.")
        return
    batch_id = uuid.uuid4().hex[:10]
    USER_BATCHES[key] = {"id": batch_id, "owner": user_id, "chat_id": message.chat.id, "items": [], "failed": [], "collecting": True, "running": False, "sinhala": False}
    await message.reply_text(
        "『 📦 NEW BATCH 』\nFiles 50ක් දක්වා දැන් forward/send කරන්න.\n"
        "පහත global setting එක තෝරලා files add කරන්න. අවසානයේ /batchdone යවන්න.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Sinhala Tag: ON", callback_data=f"batchcfg:{batch_id}:on"), InlineKeyboardButton("OFF", callback_data=f"batchcfg:{batch_id}:off")],
            [InlineKeyboardButton("⛔ Cancel Batch", callback_data=f"batchcancel:{batch_id}")],
        ]),
    )


@app.on_callback_query(filters.regex(r"^batchcfg:"))
async def batch_config_callback(_, callback):
    _, batch_id, value = callback.data.split(":")
    key = (callback.message.chat.id, callback.from_user.id)
    batch = USER_BATCHES.get(key)
    if not batch or batch.get("id") != batch_id:
        await callback.answer("Batch expired.", show_alert=True); return
    batch["sinhala"] = value == "on"
    await callback.answer("Global setting saved")
    await callback.message.edit_text(f"Batch setting: Sinhala tag {'ON' if batch['sinhala'] else 'OFF'}\nNow send/forward up to 50 files, then /batchdone.")


@app.on_message(filters.command("batchdone"))
async def batch_done_command(_, message: Message):
    key = (message.chat.id, message.from_user.id if message.from_user else 0)
    batch = USER_BATCHES.get(key)
    if not batch or not batch.get("collecting"):
        await message.reply_text("Active batch එකක් නැහැ. /batch දාලා පටන් ගන්න."); return
    if not batch["items"]:
        await message.reply_text("Batch එකට files එකතු කරලා නැහැ."); return
    batch["collecting"] = False; batch["running"] = True
    batch["task"] = asyncio.create_task(run_batch(batch, message))


@app.on_message(filters.command("cancelbatch"))
async def cancel_batch_command(_, message: Message):
    key = (message.chat.id, message.from_user.id if message.from_user else 0)
    batch = USER_BATCHES.get(key)
    if not batch:
        await message.reply_text("Active batch එකක් නැහැ."); return
    batch["cancelled"] = True; batch["items"].clear(); batch["failed"].clear(); batch["collecting"] = False
    if batch.get("task") and not batch["task"].done():
        batch["task"].cancel()
    await message.reply_text("⛔ Batch queue සහ failed list එක clear කළා.")


@app.on_callback_query(filters.regex(r"^batchcancel:"))
async def batch_cancel_callback(_, callback):
    batch_id = callback.data.split(":", 1)[1]
    key = (callback.message.chat.id, callback.from_user.id)
    batch = USER_BATCHES.get(key)
    if not batch or batch.get("id") != batch_id:
        await callback.answer("Batch expired.", show_alert=True); return
    batch["cancelled"] = True; batch["items"].clear(); batch["failed"].clear(); batch["collecting"] = False
    if batch.get("task") and not batch["task"].done():
        batch["task"].cancel()
    await callback.answer("Batch cancelled")
    await callback.message.edit_text("⛔ Batch cancelled. Queue and failed list cleared.")


@app.on_callback_query(filters.regex(r"^batchfix:"))
async def batch_fix_callback(_, callback):
    _, batch_id, index = callback.data.split(":")
    key = (callback.message.chat.id, callback.from_user.id)
    batch = USER_BATCHES.get(key)
    if not batch or batch.get("id") != batch_id:
        await callback.answer("Batch expired.", show_alert=True); return
    item_index = int(index)
    if item_index >= len(batch.get("failed", [])):
        await callback.answer("Failed item not found.", show_alert=True); return
    BATCH_FIX_WAIT[key] = (batch_id, item_index)
    await callback.answer("Send the correct movie/series name")
    await callback.message.reply_text(f"File: {batch['failed'][item_index]['original']}\nදැන් නිවැරදි Movie/Series නම text එකක් ලෙස එවන්න.")


@app.on_callback_query(filters.regex(r"^cancel:"))
async def cancel_callback(_, callback):
    token = callback.data.split(":", 1)[1]
    job = PENDING.get(token) or ACTIVE_JOBS.get(token)
    if not job:
        await callback.answer("Job එක හමු වුණේ නැහැ.", show_alert=True)
        return
    if job.get("owner") and job["owner"] != callback.from_user.id:
        await callback.answer("වෙන user කෙනෙකුගේ job එක cancel කරන්න බැහැ.", show_alert=True)
        return
    flag = CANCEL_FLAGS.setdefault(token, asyncio.Event())
    flag.set()
    task = job.get("task")
    if task and not task.done():
        task.cancel()
    PENDING.pop(token, None)
    await callback.answer("Job cancelled")
    try:
        await callback.message.edit_text("⛔ Job cancelled by owner.")
    except Exception:
        pass


@app.on_message(filters.document | filters.video)
async def media_handler(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    batch = USER_BATCHES.get((message.chat.id, user_id))
    if batch and batch.get("collecting"):
        if len(batch["items"]) >= 50:
            await message.reply_text("Batch limit එක 50 files. /batchdone යවන්න.")
            return
        media = message.video or message.document
        original = (media.file_name if media else "") or "media.mp4"
        batch["items"].append({"chat_id": message.chat.id, "message_id": message.id, "original": original})
        await message.reply_text(f"Batch file {len(batch['items'])}/50 එකතු කළා.")
        return
    await run_media_serially(message)


@app.on_message(filters.forwarded)
async def forwarded_channel_handler(_, message: Message):
    """When Add Channel is waiting, a forwarded post resolves private channels without a username."""
    key = (message.chat.id, message.from_user.id if message.from_user else 0)
    if key not in CHANNEL_WAIT:
        return
    token = CHANNEL_WAIT.pop(key)
    try:
        origin = getattr(message, "forward_origin", None)
        chat = getattr(origin, "chat", None) or getattr(message, "forward_from_chat", None)
        if not chat:
            raise RuntimeError("Forwarded message එකේ channel details නැහැ. Channel එකෙන් direct post එකක් forward කරන්න.")
        title = await register_channel(message.from_user.id, chat)
        await message.reply_text(f"✅ Private/Public channel added: {title}\n📤 Send to Channel button එකෙන් යවන්න.", reply_markup=channels_markup(message.from_user.id))
    except Exception as exc:
        logging.exception("forwarded channel add failed")
        await message.reply_text(f"Channel add failed: {exc}\nBot එක channel එකට administrator කරලා channel post එකක් forward කරන්න.")


@app.on_message(filters.text & filters.regex(r"^(?!/).*") )
async def manual_title(_, message: Message):
    key = (message.chat.id, message.from_user.id if message.from_user else 0)
    if key in CHANNEL_WAIT:
        token = CHANNEL_WAIT.pop(key)
        value = message.text.strip()
        try:
            forwarded_origin = getattr(message, "forward_origin", None)
            forwarded_chat = getattr(forwarded_origin, "chat", None) or getattr(message, "forward_from_chat", None)
            chat = forwarded_chat if forwarded_chat else await app.get_chat(value)
            title = await register_channel(message.from_user.id, chat)
            await message.reply_text(f"✅ Channel added: {title}\nදැන් processed post එකේ 📤 Send to Channel button එක ඔබන්න.", reply_markup=channels_markup(message.from_user.id))
        except Exception as exc:
            logging.exception("channel add failed")
            await message.reply_text(f"Channel add failed: {exc}\nPublic සඳහා @username/-100... ID එකක් හෝ private channel එකෙන් forward කළ message එකක් නැවත එවන්න.")
        return
    if key in BATCH_FIX_WAIT:
        batch_id, item_index = BATCH_FIX_WAIT.pop(key)
        batch = USER_BATCHES.get(key)
        if batch and batch.get("id") == batch_id and item_index < len(batch.get("failed", [])):
            item = batch["failed"][item_index]
            await show_search_buttons(message, message.text.strip(), {**item, "batch_fix": True, "batch_id": batch_id, "failed_index": item_index})
            return
    pending = MANUAL_WAIT.get(key)
    if pending and time.monotonic() - pending.get("created", 0) <= 600:
        media_info = MANUAL_WAIT.pop(key)
        await show_search_buttons(message, message.text.strip(), media_info)
    elif pending:
        MANUAL_WAIT.pop(key, None)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            body = b'{"ok":true,"service":"sadesha-thumbnail-bot"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, *_):
        return


def run_health_server():
    ThreadingHTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()


async def configure_bot_commands():
    await app.set_bot_commands([
        BotCommand("start", "Open the main menu"),
        BotCommand("settings", "Configure rename, thumbnail and send mode"),
        BotCommand("channels", "Manage saved public/private channels"),
        BotCommand("thumb", "Search a thumbnail"),
        BotCommand("search", "Search IMDb titles"),
        BotCommand("batch", "Start a multi-file batch"),
        BotCommand("batchdone", "Start the collected batch"),
        BotCommand("cancelbatch", "Cancel the active batch"),
        BotCommand("cancel", "Cancel the current job"),
        BotCommand("status", "Show server and transfer status"),
        BotCommand("queue", "Show active jobs"),
        BotCommand("history", "Show completed jobs"),
    ])


async def main():
    await app.start()
    await configure_bot_commands()
    logging.info("Bot started: commands registered; Pyrogram workers=%s transmissions=%s", PYROGRAM_WORKERS, MAX_CONCURRENT_TRANSMISSIONS)
    try:
        await idle()
    finally:
        await app.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)
    logging.info("Starting Sadesha Films bot")
    threading.Thread(target=run_health_server, daemon=True).start()
    app.run(main())
