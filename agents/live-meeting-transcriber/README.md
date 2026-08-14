# Live Meeting Transcriber

Near-live transcription for a call, meeting, or interview happening now. `live_transcribe.py` captures audio with ffmpeg, cuts it into short segments, and streams each finished segment through the same free Groq Whisper endpoint the batch path uses. Lines print as they land, about one segment behind (default 15 s). On Ctrl-C it finalizes one `transcript.txt` for the notes step.

## Why this is its own skill

This is the mic-bound half of what used to be a single meeting-transcriber agent. The two halves have different constraints:

- [`meeting-transcriber`](../meeting-transcriber/) is portable: file in, notes out. It runs anywhere Python and the Groq API are reachable, including a Cowork cloud session, and is the shareable half.
- This skill is not. It needs the Mac's microphone (and optionally a BlackHole virtual audio device), so it only runs in Claude Code on the machine itself. No cloud session has an audio device, and no packaging choice changes that.

The two share one Groq implementation: `live_transcribe.py` imports its upload plumbing from `../meeting-transcriber/scripts/transcribe.py`, so the ~15 MB encoding lessons and API handling live in one place. The folders must stay siblings in this repo.

The finalized transcript feeds the meeting-transcriber notes step (speaker attribution, TL;DR, decisions, action items). This skill produces the raw material, not the deliverable.

## Setup

1. **Groq key.** Same convention as the batch path: `GROQ_API_KEY` in `~/.marketing-agents.env` (free at [console.groq.com/keys](https://console.groq.com/keys)).
2. **ffmpeg.** `brew install ffmpeg`.
3. **BlackHole**, only for capturing a call's far side. See below.

## How to run

```bash
# one-time: list capture devices to find your device's index
python3 scripts/live_transcribe.py --list-devices

# start a live session (Ctrl-C to stop and finalize)
python3 scripts/live_transcribe.py --device <index> --segment 15

# tune segment length / language / output location
python3 scripts/live_transcribe.py --device 2 --segment 12 --language en --session ~/calls/acme
```

Outputs land in a `live-<timestamp>/` session dir: `live.transcript.txt` (streamed as you go) and `transcript.txt` (finalized on stop). Hand `transcript.txt` to the meeting-transcriber notes step.

## Capturing both your mic and the call's far side (macOS)

ffmpeg records one input device, and no built-in device hears both your mic and the call audio at once. The fix is a virtual audio device:

1. **Install BlackHole:** `brew install blackhole-2ch`. This installs an audio driver, so you'll be prompted for your password; log out and in if it doesn't appear.
2. **Hear and capture the call.** Open **Audio MIDI Setup** → **＋** → *Create Multi-Output Device*. Check **BlackHole 2ch** and your headphones/speakers. Set this Multi-Output as the system output (or the call app's output) so the far side plays to your ears and into BlackHole.
3. **Combine mic + call for ffmpeg.** In Audio MIDI Setup → **＋** → *Create Aggregate Device*. Check your **microphone** and **BlackHole 2ch**. This aggregate is what you pass as `--device`.
4. Run `--list-devices` and use the aggregate device's index.

Mic-only needs none of this; it already covers an in-person room. If BlackHole isn't set up, the agent offers mic-only rather than silently dropping the far side.

## Notes and limits

- **Near-live, not word-by-word.** About one segment of lag, and each segment is transcribed without cross-boundary context, so a word can split oddly at a seam. The notes step cleans these up.
- **No diarization.** Speaker turns are inferred later, from context, in the notes step. If you need "who said what" from the audio itself, Spokenly's local models, Deepgram, or AssemblyAI do real diarization.
- Honors `GROQ_BASE_URL` to route through the Cloudflare AI Gateway for cost tracking, like the rest of this repo. Direct-to-Groq is the default.
- Live session dirs are meeting content: gitignored, never committed.
