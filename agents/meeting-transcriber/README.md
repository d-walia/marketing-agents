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

Get a free key at [console.groq.com/keys](https://console.groq.com/keys) and add
it to `~/.marketing-agents.env` (the repo's convention — never commit keys):

```
GROQ_API_KEY=gsk_...
```

Nothing to install — the script is standard-library only.

## Running it

From the repo root in Claude Code, just ask — the `meeting-transcriber`
subagent (defined in [`.claude/agents/`](../../.claude/agents/)) triggers on
requests like "transcribe this call and pull the action items."

Direct script use (Groq path):

```bash
python3 agents/meeting-transcriber/scripts/transcribe.py meeting.m4a --diarize-hint
python3 agents/meeting-transcriber/scripts/transcribe.py call.mp3 --language en
```

It writes `<file>.transcript.txt` (plain) and `<file>.timestamped.txt`
(per-segment timestamps) next to the input, and prints the transcript to stdout.

## Notes & limits

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
