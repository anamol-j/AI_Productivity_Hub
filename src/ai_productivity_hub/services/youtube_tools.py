from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/")
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [""])[0]
    match = re.search(r"([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else ""


def fetch_transcript(url: str) -> list[dict]:
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract a YouTube video ID from the provided URL.")
    return YouTubeTranscriptApi.get_transcript(video_id)


def transcript_to_text(transcript: list[dict]) -> str:
    return " ".join(item.get("text", "") for item in transcript)


def important_timestamps(transcript: list[dict], limit: int = 5) -> list[str]:
    timestamps: list[str] = []
    step = max(len(transcript) // max(limit, 1), 1)
    for item in transcript[::step][:limit]:
        start = int(item.get("start", 0))
        minutes, seconds = divmod(start, 60)
        timestamps.append(f"{minutes:02d}:{seconds:02d} - {item.get('text', '')}")
    return timestamps
