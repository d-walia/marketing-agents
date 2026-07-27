---
name: meeting-transcriber
description: Turn a meeting, sales call, customer interview, or discovery recording into structured notes — a clean transcript plus TL;DR, decisions, and an action-item table. Use whenever Dhruv asks to transcribe a call or recording, take notes from a meeting, pull action items or decisions out of a conversation, summarize an interview, or clean up a raw transcript — including when he just drags in an audio or video file and asks what's in it. For transcribing a call happening live right now, use the live-meeting-transcriber skill instead; its finished transcript comes back here for the notes step.
---

# Meeting Transcriber

Turn a recording into notes someone can act on without re-listening. Transcription is the cheap part; the structure added afterward is the product.

**Runs from anywhere.** Scripts are referenced by absolute path, and the `meeting-transcriber` subagent is installed at user level (`~/.claude/agents/meeting-transcriber.md`, symlinked to this repo), so no `cd` is needed — recordings usually live on the Desktop, not in the repo.

**Repo location.** Commands below reach the repo through `$REPO` so they work wherever it was cloned. Set it first in any shell that runs them:

```bash
REPO="${MARKETING_AGENTS_ROOT:-$HOME/github/marketing-agents}"
```

If the clone lives anywhere other than `~/github/marketing-agents`, export `MARKETING_AGENTS_ROOT` once in `~/.zshrc` and every skill follows.

## Step 1 — Resolve the input file

Do this before anything else, and never skip to transcription on a guessed path.

- **If a path was given** (dragged in, pasted, quoted): use it verbatim. Do not retype it.
- **If no path was given**: glob the likely locations rather than asking Claude to recall a filename —

  ```bash
  ls -lh ~/Desktop/*.{m4a,mp3,wav,mp4,mov} ~/Downloads/*.{m4a,mp3,wav,mp4,mov} 2>/dev/null
  ```

  Then show the candidates with size and duration and **ask which one**. Never pick between similarly-named recordings on your own — screen recordings from the same session differ by a couple of characters and picking wrong costs a long extraction pass.

### Never retype a filename

macOS screen recordings contain a **narrow no-break space (`U+202F`)** before "AM"/"PM". It renders identically to a normal space and is a different byte sequence — retyping the name produces `No such file or directory` on a file that plainly exists.

So: always pass paths through from a glob or from what the user supplied, always quote them, and use tab-completion or `ls` output rather than transcription of a displayed name. If a file "doesn't exist" but you can see it, this is why — recover with a glob:

```bash
ls -b ~/Desktop/*.mov          # -b reveals the escape sequences
```

## Step 2 — Triage size before transcribing

Groq documents a **25 MB** upload cap, but **treat ~15 MB as the real ceiling** — see below. Recordings routinely run into the gigabytes, so check first:

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "<file>"
```

| Situation | Action |
|---|---|
| Audio file already under ~15 MB | Transcribe directly |
| Video (`.mp4`/`.mov`/…), any size | Extract audio first — always |
| Audio over ~15 MB | Re-encode to 16 kHz mono **at 32k** before transcribing |
| `ffprobe` returns nothing | The file may be truncated or still being written. Say so; don't proceed |

**Encode at 32k. Not 48k.** 32k ≈ 0.23 MB/min, so ~60 min lands near 13 MB and a 2-hour recording still fits:

```bash
ffmpeg -i "<input>" -vn -ac 1 -ar 16000 -c:a aac -b:a 32k "<name>.m4a"
```

Whisper is speech-recognition, not audiophile playback — 32k mono at 16 kHz costs nothing in transcription accuracy and buys a large margin against the ceiling.

### Why ~15 MB, not 25 MB

Measured on 2026-07-25 against a 57-minute recording:

| Size | Result |
|---|---|
| 358 KB (60 s clip) | ✅ transcribed |
| 13 MB (32k, full) | ✅ transcribed |
| 21.5 MB (48k, full) | ❌ `[Errno 32] Broken pipe` mid-upload |
| 42 MB (original) | ❌ over cap |

21.5 MB is comfortably under Groq's documented 25 MB and still failed — the connection dropped while sending the body, which points at a network/proxy body limit rather than Groq rejecting it. The API itself was reachable and the key valid throughout (verified separately). So the documented cap is not the binding constraint; **encode for ~15 MB and the question doesn't arise.**

A broken pipe on upload is therefore a *size* symptom, not an auth or connectivity one. Re-encode smaller before touching the key or the network.

Write extracted audio to the scratch area or alongside the source — never into `Claude Outputs/`, which is for deliverables.

**Never chunk a file silently to get under the ceiling.** If a recording won't fit even at 32k (roughly 2 hours+), say so and offer the local fallback (Spokenly does real diarization and has no cap, but this agent does not drive it).

## Step 3 — Get a transcript

- **A transcript already exists** (`.txt`/`.md`/`.vtt`/`.srt`, or pasted text) → skip transcription entirely, go to Step 4.
- **Live / in-progress** ("transcribe as I go", a call happening now) → that's the **`live-meeting-transcriber`** skill (`agents/live-meeting-transcriber/`). It needs the Mac's microphone, so it only runs in Claude Code on the machine — hand off to it; its finalized `transcript.txt` comes back to this skill's Step 4 for speaker attribution and notes.
- **A finished recording** → 

  ```bash
  REPO="${MARKETING_AGENTS_ROOT:-$HOME/github/marketing-agents}"
  python3 "$REPO/agents/meeting-transcriber/scripts/transcribe.py" "<audio>" --no-speaker-labels
  ```

  Needs `GROQ_API_KEY` in the environment or `~/.marketing-agents.env`. If it's missing, stop and point at https://console.groq.com/keys — do not proceed without it.

## Step 4 — Always produce a speaker-attributed transcript

**The raw Whisper output is one undifferentiated wall of text and is not a deliverable.** An 11,000-word block with no turns, no paragraphs, and no speaker labels is unreadable — never hand it over as "the transcript." Whisper's output is an intermediate artifact. The transcript a person can actually use is one you construct.

Dispatch the **`meeting-transcriber` subagent** with the resolved transcript path. Transcripts are long; running this in a subagent keeps the full text out of the main conversation and returns only the deliverable. Give it **both** files — the plain transcript for wording, the `.timestamped.txt` for the timestamps that anchor each turn.

Two deliverables come out of this step, always:

1. **`<slug>-<date>.speakers.md`** — the readable transcript: one paragraph per turn, `**Name** [MM:SS]` at the head of each, disfluencies removed. This is what someone opens when they want to read the conversation.
2. **`<slug>-<date>.notes.md`** — Meeting / TL;DR / Decisions / Action items / Open questions, per the subagent definition.

Produce the speaker transcript even when only "a transcript" was asked for. The plain wall of text is never the right answer to that request.

### How to attribute speakers honestly

There is **no diarization on this path** — Whisper does not identify speakers, and `--no-speaker-labels` only stamps a warning. Attribution is inference, and it must be labeled as such:

- **State it up front**, in a header block on the transcript itself: labels are inferred from context, not from the audio.
- **Infer from evidence in the text**: self-introductions, who demos or shares a screen, who asks versus answers, who is addressed by name, role-specific claims ("at my company we…").
- **Mark genuinely ambiguous turns** inline rather than guessing silently. A handful of `*[speaker unclear]*` notes cost the reader nothing; a confidently wrong label is a fabricated quote.
- **Never invent a name.** If someone is only "the second voice," say that. Names come from the audio or from what the user told you — nowhere else.
- **Never guess at unclear audio.** `[inaudible]` is the answer. Do not write a plausible-looking word with a `(?)` after it, and never do both at once — a guess plus a disclaimer is still a guess.

### Trim duplicated content

Recordings often replay their opening, or contain a false start before the real one. Compare the tail against the head; if the last minutes repeat earlier content, omit the duplicate and say so in the header. Report the true content range (e.g. content runs `[00:00]–[54:12]`, replay after).

## Step 5 — Where output goes

**Deliverables go to `~/Desktop/Claude Outputs/`**, not loose on the Desktop and not next to a recording buried in Downloads:

```
~/Desktop/Claude Outputs/<meeting-slug>-<YYYY-MM-DD>.speakers.md   # readable transcript
~/Desktop/Claude Outputs/<meeting-slug>-<YYYY-MM-DD>.notes.md      # summary + actions
```

Intermediate artifacts — `.transcript.txt`, `.timestamped.txt`, extracted `.m4a` — stay next to the source. They're working files, they're gitignored, and they don't belong in an outputs folder. **Never point the user at a raw `.transcript.txt` as the result.**

Report both paths when finished, plus the TL;DR inline so the result is readable without opening a file.

## Privacy

Recordings are meeting content — client calls, interviews, internal discussions. The repo's `.gitignore` already excludes audio, video, transcripts, and notes; keep it that way and never commit meeting content. For a recording flagged sensitive, say plainly that Groq is a third-party API and offer the local fallback instead of uploading.
