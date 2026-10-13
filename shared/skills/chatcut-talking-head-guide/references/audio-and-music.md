## Track roles (turn on auto-ducking)

Desktop stores ducking on the Flux `MemoryTrackModel.audioDucking` field. Set it with `edit_track`; do not pass a top-level `role` or `audioRouting` field.

- The talking / interview / lecture track (and any voiceover / narration) is the **anchor**: update it with `{"audioDucking":{"role":"anchor"}}`. This is the track everything else ducks under — set it, or nothing ducks.
- Background music, ambient beds, and b-roll audio beds that should sit under speech are **followers**: update them with `{"audioDucking":{"role":"follower"}}`.
- Short sound effects (SFX), stingers, hits, whooshes, clicks, and other editorial accents usually stay out of ducking.
- To turn ducking off for a track, update it with `{"audioDucking":null}`.

For a follower, optional `duckDepthDb`, `attackMs`, and `releaseMs` belong inside `audioDucking`. Omit them to use the engine defaults unless the user asks for a specific ducking response.

**Read the existing layout first.** Before creating tracks or placing new clips, read the current track names and roles — if a track is already tagged for this content (a `follower` named "Music", an `anchor` named "VO"), put the new clip there and match its role; only make a new track when nothing fits. **Organize before you assign — roles are per-track, so aim for one role per track.** If the same kind of content is scattered across several tracks (e.g. the voice on A1 _and_ A3), consolidate it onto one track _first_: move the clips with `edit_item` (`updates[].trackId`), then delete the emptied track by id with `edit_track`. Then assign the role once. While you're laying tracks out, stack them the way a mixer reads a session — **voice/VO on A1, the top audio lane; music below it** — and give each a short name like "VO" or "Music" so the spoken word stays easy to find. A sensible default, not a rule; follow the user's intent when the layout should differ. Keep deliberate separation, though — two _different_ speakers, clips that overlap in time, or intentional layering each stay on their own track (and each still gets its role). After assigning, read the project back to confirm every track that should anchor/duck does, and that you left the music's base volume alone.

---

## Background Music

### Goal

Set the mood and smooth over micro-gaps in speech.

### Principles

- Set the music track's `audioDucking.role` to `follower` with `edit_track` (and the talking track's `audioDucking.role` to `anchor`). That single pair turns on auto-ducking — the engine dips the music under speech and lifts it back in the gaps.
- Pass `audioDucking.duckDepthDb` only when the user explicitly wants the music louder or softer under speech; otherwise use the engine default.
- Keep the BGM clip's base `decibelAdjustment` natural by default. Do not pre-duck music with a large negative clip gain, then also set manual `duckDepthDb`; only do both when the user explicitly asks for a lower overall bed and a stronger / weaker speech duck.
- Do not put short sound effects (SFX) or stingers on follower tracks by default. Place them at their editorial moment and adjust item volume only if they are clearly too loud or too quiet.
- No prominent lyrics
- Fade BGM in/out with `audioFadeIn` / `audioFadeOut` in seconds, usually 1-2 seconds. Do not pass frame counts to these fields.
- Tone matches content

### Fit to duration

Fit BGM to the final video extent after A-roll timing is finalized. The target duration runs from the BGM start to the real content end (video / visual / speech items), excluding the BGM itself so music never extends the render.

- Unless the user specifies a different BGM start, start BGM at frame 0.
- If generated BGM is longer than the target, place one `audio` item at the BGM start, set its duration to the target duration, and add a fade out. Do not let the full music asset run past the last visual item.
- If generated BGM is shorter than the target, do not stretch one audio item past the asset length; it will end in silence. Instead, tile multiple `audio` items until the target is covered.
- Before placing tiled BGM, calculate how many segments are needed to cover the full target duration, accounting for the planned 1-2 second overlaps. Place all segments in one pass so the whole timeline is covered, then trim the final segment to the target end.
- For tiled BGM, use alternating audio tracks (for example A2/A3) so adjacent repeats can overlap by 1-2 seconds. Fade out the earlier segment and fade in the next segment over the overlap.

### How the engine ducks music

Ducking is automatic once the music track's `audioDucking.role` is `follower`: the engine dips the track under audible `anchor` tracks (the speech / voice), and lifts it back to full level in pauses and the outro. This needs both halves — the music track is a follower **and** the talking track is an anchor (see Track roles above). If nothing is an anchor, nothing ducks and the music stays at full level.

Set music to a normal, audible base level where there is no speech. To tune the dip under speech, set `duckDepthDb` inside the follower track's `audioDucking` object. Do not solve speech clarity by heavily lowering the clip and also manually deepening the duck. To keep a track out of ducking entirely (for example a stinger that should punch through), set `audioDucking` to `null`.

---
