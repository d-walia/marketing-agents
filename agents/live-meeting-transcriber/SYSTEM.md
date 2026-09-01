# Live Meeting Transcriber

*Near-real-time transcription of a call happening now (Mac mic + optional BlackHole), producing a raw transcript that hands off to the notes step.*

Documented together with the batch transcriber — see **[Meeting Transcription (batch + live)](../meeting-transcriber/SYSTEM.md)**. The live agent captures 15s WAV segments via ffmpeg and imports the batch skill's `transcribe.py` plumbing (the two folders must stay siblings), then feeds the shared notes subagent.
