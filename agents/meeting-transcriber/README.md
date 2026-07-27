# Meeting Transcriber

Turns a meeting, sales call, customer interview, or discovery recording into
notes you can act on without re-listening: a clean transcript plus a TL;DR,
decisions, and an action-item table. Speaker turns are inferred from context,
not diarized — see the note on `--no-speaker-labels` below.

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
| Max file size | 25 MB documented — **~15 MB in practice** |

A one-hour meeting is a single request, well under the ceilings — the only real
constraint is file size, and the documented 25 MB is not the number to plan
against (a 21.5 MB upload failed in testing; see [Notes & limits](#notes--limits)).
Encode at 32k and an hour lands near 13 MB. Spokenly's local models remain the
fallback for oversized or highly sensitive recordings (no caps, on-device, real
speaker diarization), but this agent does not drive it.

## Setup

1. **Get a free Groq key** at [console.groq.com/keys](https://console.groq.com/keys)
   and add it to `~/.marketing-agents.env` (the repo's convention — never commit
   keys):

   ```
   GROQ_API_KEY=gsk_...
   ```

2. **Install ffmpeg** — needed for the video-file path (the plain
   audio-file path is standard-library only and needs nothing):

   ```bash
   brew install ffmpeg
   ```

For transcribing a call **happening live right now**, see the sibling
[`live-meeting-transcriber`](../live-meeting-transcriber/) skill — it captures
from the Mac's microphone (optionally plus the call's far side via BlackHole),
so it is mic-bound and Claude Code-only by nature. Everything in *this* folder
is portable: file in, notes out, no hardware dependency.

## How to use it

The easiest way is to **just ask, and drag the file into the prompt**:

> *transcribe this call and pull the action items*

[`SKILL.md`](SKILL.md) is the front door. It resolves the input file, triages it
against Groq's 25 MB cap (extracting audio from video when needed), picks the
right mode, then hands off to the `meeting-transcriber` subagent — defined in
[`.claude/agents/`](../../.claude/agents/) — which writes the notes. Install it
by symlinking this folder into `~/.claude/skills/`:

```bash
ln -s ~/github/marketing-agents/agents/meeting-transcriber ~/.claude/skills/meeting-transcriber
```

**Drag the file in rather than typing its name.** macOS screen recordings
contain a narrow no-break space (`U+202F`) before AM/PM that looks exactly like
a normal space — retype it and the shell reports `No such file or directory` for
a file that is plainly there. Dragging from Finder inserts the real bytes.

**Two deliverables land in `~/Desktop/Claude Outputs/`:**

| File | What it is |
|---|---|
| `<slug>-<date>.speakers.md` | The readable transcript — one paragraph per turn, `**Name** [MM:SS]`, disfluencies removed |
| `<slug>-<date>.notes.md` | TL;DR, decisions, action items, open questions |

The raw `.transcript.txt` Whisper produces is **an intermediate, not a
deliverable** — it's a single unbroken block of text with no turns or speaker
labels, unreadable at meeting length. The `.speakers.md` file is the one to
open. Speaker labels are inferred from context (Whisper does not diarize) and
say so in their own header; ambiguous turns are marked rather than guessed.

Intermediate files (raw transcripts, extracted audio) stay
next to the input and are gitignored.

The two modes below are what runs under the hood, and what to run by hand.
Every mode produces a plain `transcript.txt`; hand that to the notes step to get
the TL;DR / decisions / action-item table (the subagent does this automatically).
(A third mode — a call happening live — lives in
[`live-meeting-transcriber`](../live-meeting-transcriber/); its finalized
transcript feeds the same notes step.)

### Mode 1 — a finished audio recording

```bash
python3 agents/meeting-transcriber/scripts/transcribe.py meeting.m4a --no-speaker-labels
python3 agents/meeting-transcriber/scripts/transcribe.py call.mp3 --language en
```

Writes `<file>.transcript.txt` (plain) and `<file>.timestamped.txt` (per-segment
timestamps) next to the input, and prints the transcript to stdout.

### Mode 2 — a video file (mp4/mov/etc.)

Video files are far bigger than the upload ceiling — so extract a small audio
track with ffmpeg first, then transcribe that:

```bash
# extract 16 kHz mono audio (32 kbps ≈ 0.23 MB/min → ~60 min ≈ 13 MB)
ffmpeg -i "recording.mp4" -vn -ac 1 -ar 16000 -c:a aac -b:a 32k "recording.m4a"

# then transcribe like Mode 1
python3 agents/meeting-transcriber/scripts/transcribe.py "recording.m4a" --no-speaker-labels
```

**Use 32k, not 48k.** Groq documents a 25 MB cap, but the practical ceiling is
lower — see [Notes & limits](#notes--limits). Whisper is speech recognition, not playback:
32k mono at 16 kHz costs nothing in accuracy and keeps a wide margin. Check a
file's length first with `ffprobe -i recording.mp4 -show_entries format=duration`.

## Notes & limits

- **The real upload ceiling is ~15 MB, not the 25 MB Groq documents.** Measured
  2026-07-25 on a 57-minute recording: 358 KB ✅, 13 MB (32k) ✅, **21.5 MB (48k)
  ❌ `[Errno 32] Broken pipe` mid-upload**, 42 MB ❌. The 21.5 MB failure sits
  well inside the documented cap, and the API was reachable with a valid key
  throughout — the connection dropped while sending the body, which points at a
  network/proxy body limit rather than Groq. Encode for ~15 MB at 32k and the
  question never comes up. **A broken pipe on upload means the file is too big,
  not that credentials are wrong** — re-encode smaller before debugging auth.
  Spokenly's local models are the fallback for anything oversized or highly
  sensitive.
- Whisper does not label speakers, and **`--no-speaker-labels` adds no
  diarization** — it only stamps a reminder at the top of both transcript files
  so the notes step doesn't invent names. Turns are inferred from context. If you
  genuinely need "who said what," this backend can't do it: Spokenly's local
  models do real diarization, as do Deepgram and AssemblyAI. (The flag was
  originally `--diarize-hint`, which oversold it; that spelling still works.)
- To route the Groq call through the Cloudflare AI Gateway (for cost tracking,
  like the rest of this repo), set `GROQ_BASE_URL` to your gateway's Groq
  endpoint. Direct-to-Groq is the default.
- Recordings and generated transcripts/notes are gitignored — audio and meeting
  content never land in the repo.
