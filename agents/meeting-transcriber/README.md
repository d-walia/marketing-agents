# Meeting Transcriber

Turns a meeting, sales call, customer interview, or discovery recording into
notes you can act on without re-listening: a clean speaker-attributed
transcript plus a TL;DR, decisions, and an action-item table.

Transcription is the cheap part — the agent's value is the structure it adds
after. It transcribes via the **Groq Whisper API**, which is free, headless, and
needs no app installed.

## Why Groq (and not Spokenly)

[Spokenly](https://spokenly.app/) is a *local Mac app*, not a hosted service —
there's no remote "Spokenly API." Its cloud mode just wraps third-party APIs
(Groq, OpenAI, Deepgram) with your own key. So rather than drive an app, this
agent calls **Groq directly** and skips Spokenly entirely.

Groq's free tier on `whisper-large-v3-turbo`:

| Limit | Free tier |
|---|---|
| Requests / day | 2,000 |
| Audio / clock-hour | ~2 hours (7,200 audio-seconds) |
| Max file size | 25 MB |

A one-hour meeting is a single request, well under the ceilings — the only real
constraint is the 25 MB file cap (below). Spokenly's local models remain the
fallback for oversized or highly sensitive recordings (no caps, on-device, real
speaker diarization), but this agent does not drive it.

## Setup

1. **Get a free Groq key** at [console.groq.com/keys](https://console.groq.com/keys)
   and add it to `~/.marketing-agents.env` (the repo's convention — never commit
   keys):

   ```
   GROQ_API_KEY=gsk_...
   ```

2. **Install ffmpeg** — needed for the video-file and live paths (the plain
   audio-file path is standard-library only and needs nothing):

   ```bash
   brew install ffmpeg
   ```

3. **(Live, capturing call audio only)** install BlackHole — see
   [Live capture](#live-capture-near-live) below.

## How to use it

The easiest way is to **just ask in Claude Code from the repo root** — the
`meeting-transcriber` subagent (defined in [`.claude/agents/`](../../.claude/agents/))
triggers on requests like *"transcribe this call and pull the action items"* or
*"transcribe as I go"*, picks the right mode, and writes the notes. The three
modes below are what it runs under the hood, and what to run by hand.

Every mode produces a plain `transcript.txt`; hand that to the notes step to get
the TL;DR / decisions / action-item table (the subagent does this automatically).

### Mode 1 — a finished audio recording

```bash
python3 agents/meeting-transcriber/scripts/transcribe.py meeting.m4a --diarize-hint
python3 agents/meeting-transcriber/scripts/transcribe.py call.mp3 --language en
```

Writes `<file>.transcript.txt` (plain) and `<file>.timestamped.txt` (per-segment
timestamps) next to the input, and prints the transcript to stdout.

### Mode 2 — a video file (mp4/mov/etc.)

Groq caps uploads at **25 MB**, and video files are far bigger — so extract a
small audio track with ffmpeg first, then transcribe that:

```bash
# extract 16 kHz mono audio (48 kbps ≈ 0.35 MB/min → ~70 min fits under the cap)
ffmpeg -i "recording.mp4" -vn -ac 1 -ar 16000 -c:a aac -b:a 48k "recording.m4a"

# then transcribe like Mode 1
python3 agents/meeting-transcriber/scripts/transcribe.py "recording.m4a" --diarize-hint
```

For very long videos (90 min+) drop to `-b:a 32k` (~100 min per 25 MB). Check a
file's length first with `ffprobe -i recording.mp4 -show_entries format=duration`.

### Mode 3 — a live call happening now

See [Live capture](#live-capture-near-live) below.

## Live capture (near-live)

For a call or interview happening *now*, `live_transcribe.py` captures with
ffmpeg, cuts the audio into short segments, and streams each through the same
Groq endpoint. Lines print as they land — lag is about one segment (default
15s). On Ctrl-C it finalizes one `transcript.txt` for the notes step.

```bash
brew install ffmpeg                       # one-time
python3 agents/meeting-transcriber/scripts/live_transcribe.py --list-devices
python3 agents/meeting-transcriber/scripts/live_transcribe.py --device <index> --segment 15
```

Outputs land in a `live-<timestamp>/` session dir: `live.transcript.txt`
(streamed as you go) and `transcript.txt` (finalized on stop).

### Capturing both your mic and the call's far side (macOS)

ffmpeg can only record one input device, and no built-in device hears both your
mic and the call audio at once. The fix is a virtual audio device:

1. **Install BlackHole:** `brew install blackhole-2ch` (installs an audio
   driver — you'll be prompted for your password; log out/in if it doesn't
   appear).
2. **Hear + capture the call.** Open **Audio MIDI Setup** → **＋** → *Create
   Multi-Output Device*. Check **BlackHole 2ch** and your headphones/speakers.
   Set this Multi-Output as the system output (or the call app's output) so the
   far side plays to your ears *and* into BlackHole.
3. **Combine mic + call for ffmpeg.** In Audio MIDI Setup → **＋** → *Create
   Aggregate Device*. Check your **microphone** and **BlackHole 2ch**. This
   aggregate is what you pass as `--device`.
4. Run `--list-devices` and use the aggregate device's index.

Mic-only needs none of this — it already covers an in-person room. If BlackHole
isn't set up, the agent will offer mic-only rather than silently dropping the
far side.

## Notes & limits

- **Live is near-live, not word-by-word:** ~one-segment lag, and each segment is
  transcribed without cross-boundary context, so a word can split oddly at a
  seam. The notes step cleans these up.

- Groq's free upload cap is 25 MB. For a long meeting, export to 16 kHz mono
  `.m4a` first (an hour fits easily); Spokenly's local models are the fallback
  for anything oversized or highly sensitive.
- Whisper does not label speakers — the transcript infers turns from context and
  says so in the notes.
- To route the Groq call through the Cloudflare AI Gateway (for cost tracking,
  like the rest of this repo), set `GROQ_BASE_URL` to your gateway's Groq
  endpoint. Direct-to-Groq is the default.
- Recordings and generated transcripts/notes are gitignored — audio and meeting
  content never land in the repo.
