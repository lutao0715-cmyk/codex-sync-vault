---
name: transcription
description: Use for ChatCut Desktop built-in and ACP Agent tasks involving source transcript or ASR corrections, captions, subtitles, layout, animation, translation, transcript search, speech cleanup, or transcription readiness.
---

# Transcription

For local/client-held media, import it through Desktop's `push_asset` tool, then use `browse_assets` to check whether transcription is available before transcript-dependent work.

Typical flow:

1. Use `browse_assets` to get the video/audio asset ID and transcript status.
2. If this is a fresh local import, make sure it is registered through Desktop's `push_asset` tool.
3. Call `track_progress` with `action:"wait"`, `target:"transcription"`, and `assetIds` set to the asset ID or prefix.
4. Use `find_transcript` to search transcript text and confirm word timestamps.
5. Use `edit_captions` action `enable` or `read_captions` as needed once transcription is ready.

Desktop captions derive from transcription. Editing source transcription or source clips
automatically rebuilds the affected caption tracks. Direct Card edits remain until their
source changes; unrelated edits do not rebuild them. `disable` hides captions and `enable`
shows the existing caption item while preserving each track's visibility. Use
`track` to show or hide individual language tracks. There is no dirty state or
manual regeneration step.

Example:

```json
{
  "action": "wait",
  "target": "transcription",
  "assetIds": "13c1aa02cd"
}
```

Always use `track_progress` for transcription readiness when the asset reports a transcription job. Do not upload a Desktop-local asset to cloud storage merely to make transcription available; if the local workflow cannot start transcription, report that limitation instead of switching to an external import path.

Use `trigger_transcript` when the user explicitly wants an idle or failed transcription started. It reuses prepared transcription audio and otherwise asks Desktop to run its local audio preparation/upload pipeline. It is idempotent for complete, no-audio, and in-progress assets.

## Caption refinement

Finish source corrections before polishing the derived display. Read the transcript against the speech and use `manage_transcript` FIX for confirmed ASR mistakes; preview a multi-command batch first. Preserve the speaker's meaning and do not invent missing words. `set_card_text` changes only viewer-facing caption text, so it is suitable for display wording or a translated Card, not a substitute for correcting source transcription. Finish intended clip edits as well: source changes rebuild affected caption tracks and can replace their direct Card edits.

Read `read_captions` with `words:true` and use the returned Card and token IDs. Improve sentence grouping with `split_card` and `merge_cards`, then adjust spacing and readable scale with caption style fields and `set_card_layout`. Check long phrases and short isolated words in the real video rather than assuming a maximum line length gives good phrasing. Card/token start and end times are microseconds; frame queries and frame-based placement require conversion using the project frame rate.

Batch a shared baseline style first, then re-read Cards: style changes can regroup them and invalidate old Card IDs. Use `edit_captions {action:"batch",edits:[...]}` for up to 100 ordered synchronous edits with one commit; a failing edit writes nothing. Batch independent Card layouts and styles, including multiple bindings to one template. For example, each binding is `{action:"set_card_style",cardId,style:{template:{path,runtime}},mode:"merge"}`. Do not carry old Card IDs across a regrouping style edit in the same batch. For splitting, pass `{cardId:card.id,beforeTokenId:card.words[n].id}` from a fresh `read_captions` result, choosing a word after the first. Transcript correction locations and caption split boundaries are different contracts.

Choose the few Cards whose spoken meaning warrants emphasis. Use ordinary caption styles for the baseline, and reference a reusable Motion Graphic template to those Cards through `set_card_style` and `style.template` when a custom treatment serves the request. Delegate source creation with `delegate_task` request `{action:"start",agent:"motion-graphic",output:"caption-template",name,task}`. The specialist receives the focused caption-template implementation skill. Request real caption Cards, not fixed title text. Supply representative short and long caption text, the spoken meaning, reading hierarchy, Card dimensions and timing. For expressive animation, describe how positions, rhythm and motion support that meaning; size and word highlighting alone do not satisfy a custom animated-template request. Reuse one source across distinct actual sentences, with properties for variations, while ordinary captions stay readable. Keep reusable source in a project-owned persistent location, including the project workspace. Wait for the returned `template:{path,runtime}` and pass it as `style.template`, optionally adding properties. Resume that same taskId with concrete feedback for template revisions, including after completion. Do not register a caption template in the asset library or call `push_asset`; ordinary MG asset creation/validation is not a prerequisite. The `template` action in `edit_captions` is only the built-in preset catalog.

For Remotion, the exported root receives `{ item }` and reads `item.props.caption`; caption is not a root component prop. For HTML, `mount` initially receives empty `props`; retain new values in the controller's `update({ props })` and read `props.caption` when rendering. The caption context includes `text`, `visibleText`, `words`, `frame`, `time`, `fps`, `geometry`, and Card/track IDs. Caption `start` is zero, `end` is Card duration in seconds, and word `start`/`end` are seconds relative to the Card; these are not the microseconds returned by `read_captions`. Use the actual supplied text and timings. An optional standalone preview may have no caption context. A fallback can make that preview possible, but it is not required for binding and does not verify real caption rendering.

A minimal Remotion binding (the final design still needs styling and real Card review):

```jsx
export default function CaptionTemplate({ item }) {
  const caption = item?.props?.caption;
  return <div>{caption?.text ?? "Template preview"}</div>;
}
```

Template overrides can be applied to the caption item, a track, or a Card. `template:null` explicitly chooses ordinary captions even if a parent has a template. To restore a Card's inheritance, replace its style with the remaining intended fields and omit `template`; simply omitting it from a merge leaves the old override in place. Read results retain the native source path and runtime.

Inspect representative **bound Cards** over the actual footage, including word changes and Card boundaries. A standalone MG preview or a successfully saved source reference does not validate caption rendering. Verify source corrections, grouping, spacing, text visibility, subject clearance, and emphasis across the complete clip. Reopen/read the saved project to check persistence, and inspect the requested export before claiming the refined video is finished.

## Caption Translation

Read `read_captions` first. Its `captions.tracks` includes hidden tracks and
identifies originals and translations with `role`, `contentLanguageCodes`, and
`sourceTrackId`. A null track-level `languageCode` does not mean the original
text is missing; use `contentLanguageCodes` to identify its language.

To restore existing original or bilingual subtitles, pass the hidden track's
returned `showAction` directly to `edit_captions`. To hide a language, use
`action: "track"` with its exact `trackId` and `visible: false`. Use `enable`
first only if `captions.visible` is false. Verify the resulting track visibility
with `read_captions`.

Use `edit_captions` action `translate` only to create or update a translation
in a language the user requested. Do not use translation to restore visibility,
invent a target language, or create a temporary translation and hide it.
Enable captions if none exist, then pass the requested target language in `json`:

```json
{
  "action": "translate",
  "json": "{\"languageCode\":\"es\",\"mode\":\"bilingual\"}"
}
```

This creates or updates a separate translation track. `mode` defaults to
`bilingual`; use `translation` to hide the source captions and show the translation.
Optional `trackId` in the payload selects a source caption track or its source
media track by id/prefix; omit it to translate visible source tracks and sources
with a visible translation in the target language.
Use `set_card_text` for individual wording corrections after translation.

## Stuck Transcription And Retry

Do not declare transcription stuck from one non-terminal status. Base the decision on both asset length and the time the local CLI has actually waited in this task.

1. Use `browse_assets` and note the asset duration when available.
2. Start counting elapsed wait time from the first `track_progress` `action:"wait"` or from the earliest reliable in-task timestamp where Codex observed transcription as pending/running.
3. Treat `no_audio` / no-speech as a successful terminal analysis result: the media is usable, but there is no transcript to read or caption. Do not report it as a transcription failure or retry it unless the user says the media contains speech that should have been detected.
4. If transcription reports an explicit failed, errored, or timed-out terminal state, retry immediately after confirming the asset is a registered video/audio asset and its local source is still available.
5. If transcription remains pending/running with no failure, treat it as stuck only after elapsed wait time exceeds `max(5 minutes, min(60 minutes, 2 × asset duration))`. For example, wait at least 5 minutes for a 30-second clip, about 20 minutes for a 10-minute asset, and about 60 minutes for a 1-hour or longer asset.
6. `action:"wait"` keeps one tool call pending until the current attempt reaches a terminal state. Do not repeatedly call `status` while it waits. A client/tool timeout ends the wait, not necessarily the transcription; inspect its explicit result before deciding whether to wait again. Cancelling a wait does not cancel the transcription.

For an `idle` or explicitly failed (`error`) run, use `trigger_transcript` with the asset id/prefix. It does not wait for completion. After triggering, call `track_progress` with `target:"transcription"`, `action:"wait"`, and the same asset id before reading transcripts or captions. Desktop `manage_transcript` only repairs transcript text and speaker assignments; it does not retry transcription. If a running job genuinely exceeds the stuck threshold, report that it cannot be force-retried through the current Desktop tool surface instead of calling an unsupported action.

If captions read back as empty, check the source-time range of the timeline clip. A transcript can be ready while the current visible clip starts before the first spoken word; add or trim a clip so the transcribed source words fall inside the timeline range, then extend/update the captions item duration if needed.

Use the raw tools when you need finer control:

- `track_progress` with `target: "transcription"` for status/wait.
- `find_transcript` for query-based transcript lookup.
- `read_captions` and `edit_captions` for caption display edits.
- `manage_transcript` action `fix` for source transcript repair.
- `clean_script` for mechanical timeline playback cleanup of fixed fillers and batch pauses after transcript-ready media is on the timeline.

When a transcript-ready request becomes an editorial talking-head edit, follow the public-safe talking-head workflow in shared `talking-head-guide`. In short: use `clean_script` only for mechanical cleanup, then use Script (`read_script` -> edit `timeline.md` -> `apply_script`) for semantic repeated-take, silence, filler, or coherence edits, and verify the resulting script rather than trusting tool success alone.
