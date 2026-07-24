#!/usr/bin/env python3
"""Transcribe an audio file via the Groq Whisper API — the free, headless
backend for the meeting-transcriber agent.

Usage:
    python3 transcribe.py meeting.m4a
    python3 transcribe.py call.mp3 --language en --out notes/call.transcript.txt

Reads GROQ_API_KEY from the environment, or from ~/.marketing-agents.env.
Get a free key at https://console.groq.com/keys — the free tier covers
~2,000 transcriptions/day. Standard library only; no pip installs.

To route through the Cloudflare AI Gateway instead of hitting Groq directly,
set GROQ_BASE_URL to your gateway's Groq endpoint (…/groq/openai/v1).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "whisper-large-v3-turbo"
DEFAULT_BASE = "https://api.groq.com/openai/v1"
ENV_FILE = Path.home() / ".marketing-agents.env"
MAX_BYTES = 25 * 1024 * 1024  # Groq free-tier upload cap


def load_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key.strip()
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):]
            if line.startswith("GROQ_API_KEY"):
                _, _, val = line.partition("=")
                return val.strip().strip('"').strip("'")
    return None


def build_multipart(fields: dict, filename: str, file_bytes: bytes, content_type: str):
    boundary = "----marketing-agents-" + uuid.uuid4().hex
    b = boundary.encode()
    crlf = b"\r\n"
    body = bytearray()
    for name, value in fields.items():
        body += b"--" + b + crlf
        body += f'Content-Disposition: form-data; name="{name}"'.encode() + crlf + crlf
        body += str(value).encode() + crlf
    body += b"--" + b + crlf
    body += (
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()
        + crlf
    )
    body += f"Content-Type: {content_type}".encode() + crlf + crlf
    body += file_bytes + crlf
    body += b"--" + b + b"--" + crlf
    return bytes(body), boundary


def transcribe(path: Path, key: str, language: str | None) -> dict:
    file_bytes = path.read_bytes()
    if len(file_bytes) > MAX_BYTES:
        mb = len(file_bytes) / 1024 / 1024
        sys.exit(
            f"error: {path.name} is {mb:.1f} MB, over Groq's ~25 MB free cap.\n"
            "Compress it (export to 16 kHz mono .m4a) or use the Spokenly path."
        )
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    fields = {"model": MODEL, "response_format": "verbose_json"}
    if language:
        fields["language"] = language
    body, boundary = build_multipart(fields, path.name, file_bytes, content_type)

    base = os.environ.get("GROQ_BASE_URL", DEFAULT_BASE).rstrip("/")
    url = f"{base}/audio/transcriptions"
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"error: Groq API returned {e.code}\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"error: could not reach the API — {e.reason}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe audio via Groq Whisper.")
    ap.add_argument("audio", type=Path, help="path to the audio/video file")
    ap.add_argument("--language", help="ISO code (e.g. en) to skip auto-detect")
    ap.add_argument("--out", type=Path, help="plain-transcript output path")
    ap.add_argument(
        "--diarize-hint",
        action="store_true",
        help="note in output that Whisper does not label speakers",
    )
    args = ap.parse_args()

    if not args.audio.exists():
        sys.exit(f"error: no such file: {args.audio}")

    key = load_key()
    if not key:
        sys.exit(
            "error: no GROQ_API_KEY found.\n"
            "Add a free key from https://console.groq.com/keys to "
            f"{ENV_FILE} as:  GROQ_API_KEY=gsk_...\n"
            "(or export it in your shell)."
        )

    print(f"Transcribing {args.audio.name} via Groq {MODEL}…", file=sys.stderr)
    result = transcribe(args.audio, key, args.language)

    text = (result.get("text") or "").strip()
    segments = result.get("segments") or []
    lang = result.get("language", "unknown")

    plain_out = args.out or args.audio.with_suffix(args.audio.suffix + ".transcript.txt")
    plain_out.parent.mkdir(parents=True, exist_ok=True)
    plain_out.write_text(text + "\n")

    ts_out = args.audio.with_suffix(args.audio.suffix + ".timestamped.txt")
    if segments:
        lines = []
        for s in segments:
            start = float(s.get("start", 0))
            m, sec = divmod(int(start), 60)
            lines.append(f"[{m:02d}:{sec:02d}] {s.get('text', '').strip()}")
        note = ""
        if args.diarize_hint:
            note = "# Note: Whisper does not label speakers — infer turns from context.\n\n"
        ts_out.write_text(note + "\n".join(lines) + "\n")

    print(f"Language: {lang}", file=sys.stderr)
    print(f"Wrote {plain_out}", file=sys.stderr)
    if segments:
        print(f"Wrote {ts_out}", file=sys.stderr)
    print(text)


if __name__ == "__main__":
    main()
