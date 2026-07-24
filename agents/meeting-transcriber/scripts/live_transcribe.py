#!/usr/bin/env python3
"""Near-live transcription for the meeting-transcriber agent.

Captures audio with ffmpeg, cuts it into short segments, and transcribes each
finished segment through the same free Groq Whisper endpoint that transcribe.py
uses. Transcript lines print as they land and stream to a growing file; on
Ctrl-C the session is finalized into one plain transcript ready for the notes
step.

    # one-time: list capture devices to find your aggregate device's index
    python3 live_transcribe.py --list-devices

    # start a live session (device 2 = your "Mic + BlackHole" aggregate device)
    python3 live_transcribe.py --device 2

    # tune segment length / language / output location
    python3 live_transcribe.py --device 2 --segment 12 --language en --session ~/calls/acme

Reads GROQ_API_KEY the same way as transcribe.py (env or ~/.marketing-agents.env)
and honors GROQ_BASE_URL to route through the Cloudflare AI Gateway. Standard
library only; the sole external dependency is ffmpeg on PATH.

Capturing BOTH your mic and the call's far side needs a macOS Aggregate Device
that combines your mic with BlackHole — see the agent doc for the routing setup.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Reuse the Groq plumbing already written for the batch path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from transcribe import MODEL, DEFAULT_BASE, build_multipart, load_key  # noqa: E402


def list_devices() -> None:
    """Print ffmpeg's avfoundation capture devices (macOS)."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "avfoundation",
         "-list_devices", "true", "-i", ""],
        capture_output=True, text=True,
    )
    # ffmpeg prints the device list to stderr and exits non-zero by design.
    sys.stderr.write(proc.stderr)
    sys.stderr.write(
        "\nPick the audio index of your aggregate device (mic + BlackHole) "
        "and pass it as --device.\n"
    )


def transcribe_segment(path: Path, key: str, base: str, language: str | None) -> str:
    """POST one segment to Groq. Returns text, or '' on a recoverable error."""
    fields = {"model": MODEL, "response_format": "json"}
    if language:
        fields["language"] = language
    body, boundary = build_multipart(
        fields, path.name, path.read_bytes(), "audio/wav"
    )
    req = urllib.request.Request(
        f"{base}/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "marketing-agents-meeting-transcriber/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return (json.loads(resp.read().decode()).get("text") or "").strip()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        sys.stderr.write(f"[warn] segment {path.name}: Groq {e.code} — {detail}\n")
    except urllib.error.URLError as e:
        sys.stderr.write(f"[warn] segment {path.name}: unreachable — {e.reason}\n")
    return ""


def spawn_ffmpeg(device: str, segment: int, seg_pattern: Path) -> subprocess.Popen:
    """Start ffmpeg capturing avfoundation audio into 16 kHz mono WAV segments."""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "avfoundation", "-i", f":{device}",
        "-ac", "1", "-ar", "16000",
        "-f", "segment", "-segment_time", str(segment),
        "-reset_timestamps", "1",
        str(seg_pattern),
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def main() -> None:
    ap = argparse.ArgumentParser(description="Near-live Groq Whisper transcription.")
    ap.add_argument("--device", help="ffmpeg avfoundation audio device index/name")
    ap.add_argument("--segment", type=int, default=15,
                    help="segment length in seconds (default 15 = ~15s lag)")
    ap.add_argument("--language", help="ISO code (e.g. en) to skip auto-detect")
    ap.add_argument("--session", type=Path,
                    help="output dir (default ./live-<timestamp>)")
    ap.add_argument("--list-devices", action="store_true",
                    help="list capture devices and exit")
    args = ap.parse_args()

    if args.list_devices:
        list_devices()
        return
    if not args.device:
        sys.exit("error: --device is required (run --list-devices to find it).")

    key = load_key()
    if not key:
        sys.exit(
            "error: no GROQ_API_KEY found.\n"
            "Add a free key from https://console.groq.com/keys to "
            f"{Path.home() / '.marketing-agents.env'} as:  GROQ_API_KEY=gsk_...")
    base = os.environ.get("GROQ_BASE_URL", DEFAULT_BASE).rstrip("/")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session = args.session or Path(f"./live-{stamp}")
    seg_dir = session / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    live_txt = session / "live.transcript.txt"
    final_txt = session / "transcript.txt"

    stop = threading.Event()

    def handle_sigint(signum, frame):
        if not stop.is_set():
            sys.stderr.write("\n[stopping] finishing the last segment…\n")
            stop.set()
    signal.signal(signal.SIGINT, handle_sigint)

    sys.stderr.write(
        f"Live transcription → {session}\n"
        f"Device :{args.device}  segment {args.segment}s  press Ctrl-C to stop.\n\n"
    )
    proc = spawn_ffmpeg(args.device, args.segment, seg_dir / "seg_%05d.wav")

    # Give ffmpeg a beat; a bad device index makes it exit immediately.
    time.sleep(1.0)
    if proc.poll() is not None:
        sys.exit("error: ffmpeg exited at startup — check --device (--list-devices).")

    processed: set[Path] = set()
    parts: list[str] = []

    def drain(final: bool) -> None:
        """Transcribe finished segments. While running, the highest-numbered
        file is still being written, so hold it back until the final drain."""
        segs = sorted(seg_dir.glob("seg_*.wav"))
        ready = segs if final else segs[:-1]
        for seg in ready:
            if seg in processed or seg.stat().st_size == 0:
                continue
            processed.add(seg)
            text = transcribe_segment(seg, key, base, args.language)
            if not text:
                continue
            parts.append(text)
            ts = time.strftime("%H:%M:%S")
            line = f"[{ts}] {text}"
            print(line, flush=True)
            with live_txt.open("a") as fh:
                fh.write(line + "\n")

    try:
        while not stop.is_set() and proc.poll() is None:
            drain(final=False)
            time.sleep(1.0)
    finally:
        if proc.poll() is None:
            # 'q' asks ffmpeg to flush and close the current segment cleanly.
            try:
                proc.communicate(b"q", timeout=5)
            except Exception:
                proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        drain(final=True)

    final_txt.write_text(" ".join(parts).strip() + "\n")
    sys.stderr.write(
        f"\nDone. {len(processed)} segments.\n"
        f"Live log: {live_txt}\nFull transcript: {final_txt}\n"
        "Hand transcript.txt to the meeting-transcriber notes step.\n"
    )


if __name__ == "__main__":
    main()
