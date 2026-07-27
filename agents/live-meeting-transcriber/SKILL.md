---
name: live-meeting-transcriber
description: Transcribe a call, meeting, or interview happening live right now, near-real-time, from the Mac's microphone (optionally plus the call's far side via BlackHole). Use whenever Dhruv says "transcribe as I go", "transcribe this call live", "I'm about to get on a call — capture it", or asks for live/real-time transcription of something in progress. Mic-bound: this only works in Claude Code on the Mac itself, never in a cloud session. For a finished recording or an existing transcript, use the meeting-transcriber skill instead.
---

# Live Meeting Transcriber

Capture a conversation as it happens: ffmpeg records the Mac's audio input, cuts it into short segments, and each finished segment streams through the free Groq Whisper API. Lines print as they land (~one-segment lag); Ctrl-C finalizes a single `transcript.txt`.

**This skill is hardware-bound.** It needs the Mac's microphone (and optionally a BlackHole virtual device), so it runs only in Claude Code on the machine. A cloud session has no audio device — if that's where you are, say so and stop; do not attempt a workaround.

**The transcript is not the deliverable.** When the session ends, hand the finalized `transcript.txt` to the **`meeting-transcriber`** skill's notes step (`agents/meeting-transcriber/`, Step 4) for speaker attribution, cleanup, and the notes file. Never present the raw live transcript as the result.

## Before starting — confirm the capture path

Ask one question if it isn't obvious: **is the far side of a call needed, or just the room?**

- **Mic-only** (in-person meeting, dictation, this side of a call): works immediately, no setup.
- **Both sides of a call**: requires a macOS **Aggregate Device** combining the mic with **BlackHole** — see README for the one-time Audio MIDI Setup routing. If BlackHole isn't installed, say so *before* starting and offer mic-only rather than silently dropping the far side.

Also confirm `ffmpeg` exists (`which ffmpeg`); it's the only dependency beyond the `GROQ_API_KEY` in `~/.marketing-agents.env`.

## Running a session

```bash
# resolves wherever the repo was cloned
REPO="${MARKETING_AGENTS_ROOT:-$HOME/github/marketing-agents}"

# find the audio device index (aggregate device if capturing the call's far side)
python3 "$REPO/agents/live-meeting-transcriber/scripts/live_transcribe.py" --list-devices

# start; Ctrl-C to stop and finalize
python3 "$REPO/agents/live-meeting-transcriber/scripts/live_transcribe.py" --device <index> --segment 15
```

Outputs land in a `live-<timestamp>/` session dir next to where it runs: `live.transcript.txt` (streamed as you go) and `transcript.txt` (finalized on stop). Session dirs are working files — gitignored, never a deliverable, never in `Claude Outputs/`.

## Expectations to set

- **Near-live, not word-by-word**: ~one segment of lag (default 15 s), and each segment transcribes without cross-boundary context, so words can split oddly at seams. The notes step cleans these up — don't fight them live.
- **No speaker labels**: Whisper doesn't diarize. Attribution happens later, inferred from context, in the meeting-transcriber notes step.
- A bad `--device` index makes ffmpeg exit at startup; re-run `--list-devices` rather than guessing.

## Privacy

Live capture is meeting content. Segments upload to Groq (a third-party API) as the call happens — for a conversation flagged sensitive, say that plainly *before* starting and offer a local alternative (Spokenly) instead. Never commit session dirs; the repo's `.gitignore` already excludes them.
