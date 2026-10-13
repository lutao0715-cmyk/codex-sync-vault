---
name: transcription
description: Use for ChatCut Desktop built-in and ACP Agent tasks involving source transcript or ASR corrections, captions, subtitles, layout, animation, translation, transcript search, speech cleanup, or transcription readiness.
---

# Transcription

## Correct the words, then design the captions

1. Read the current project's placed source clips and all caption Cards covering the finished edit. Use `read_captions` with `words:true`; follow `limit`/`offset` pagination until the relevant text is complete. Read the corresponding source transcript, not just search hits for an assumed mistake. Preserve the existing picture edit and audio unless the user asks to change them.
2. Check suspicious words against the speech and context. Locate each occurrence in its source asset with `inspect_asset {assetId,transcriptRanges:[{start,end}]}`. These ranges and returned `startUs`/`endUs` are original source microseconds. Timeline position is not source position: use the placed clip's source range and speed mapping. `find_transcript` can locate phrases, but its source times are milliseconds and timeline placements are frames; neither is a FIX locator.
3. Correct confirmed ASR mistakes with `manage_transcript {action:"fix",asset,content,preview:true}` first, then apply the reviewed commands without preview. Content uses `FIX [sN]: wordIdx -> "newText"`; take the 1-based `segmentIndex` and 0-based `wordIndex` directly from `inspect_asset`. Filtering does not renumber them; silence rows are not editable words. Batch confirmed corrections per asset. Do not invent uncertain speech or silently change meaning.
4. Re-read the corrected source ranges and rebuilt captions before styling. Verify every intended occurrence, and describe unresolved uncertainty honestly. `set_card_text` only edits display wording; it cannot prove source ASR was repaired. Source or clip edits rebuild affected caption tracks and may replace direct Card edits, so complete them before layout work.

## Readable baseline and purposeful emphasis

Apply a shared readable baseline, then re-read Cards because style regrouping can invalidate IDs. Use `split_card` with `{cardId,beforeTokenId}` from fresh Card words (choose a token after the first), `merge_cards`, `set_card_layout`, and Card styles for natural phrase groups and spacing. Read each tool's schema for its exact action fields. Use `edit_captions {action:"batch",edits:[...]}` for up to 100 ordered synchronous edits with one commit; a failed edit writes nothing. Do not carry old IDs through a regrouping operation in the same batch.

When the user asks for lively, expressive captions clearly distinct from ordinary subtitles, select a few phrases whose meaning deserves emphasis. Design semantic word groups, visual hierarchy, placement, entrance/exit rhythm and motion around the speaker's available negative space. Keep faces clear. Larger type or active-word highlighting alone does not fulfill that request. The user does not need to name a template or implementation technique. Use actual short and long phrases to judge whether the composition serves the spoken meaning; keep the remaining captions calm and readable.

If `delegate_task` is available, request a reusable caption treatment:

```json
{
  "request": {
    "action": "start",
    "agent": "motion-graphic",
    "output": "caption-template",
    "name": "Expressive captions",
    "task": "Create a reusable treatment for these actual phrases: … . Their meaning is … . Use semantic grouping, hierarchy, placement and motion with clear reading time. Card dimensions/durations: … . Speaker position and free space: … . Render supplied caption words and timing; keep ordinary captions unchanged."
  }
}
```

Replace the brief's placeholders with observed content and geometry. The specialist owns implementation details. Wait for that task's returned `template:{path,runtime}`, then bind it to selected fresh Cards:

```json
{
  "action": "set_card_style",
  "cardId": "<returned Card id>",
  "style": {
    "template": {
      "path": "<returned persistent path>",
      "runtime": "<returned runtime>"
    }
  },
  "mode": "merge"
}
```

Batch multiple bindings and reuse the source across different phrases; add template properties only when supported by that source. Resume the same taskId with concrete feedback for revisions, including after completion. Do not push a caption template into the asset library. `edit_captions` action `template` lists/applies built-in presets; it does not create custom source. `template:null` chooses ordinary captions; omitting a template in a merge leaves its old override intact.

If delegation is unavailable, use the current surface's existing direct caption-creation capability and its implementation guidance. Do not claim a specialist ran or an unsupported custom treatment was created. When that surface cannot produce the requested treatment, explain the actual limitation and what was completed.

## Verify the delivered video

Inspect actual bound Cards over the footage: representative ordinary, emphasized, short and long phrases, word changes, and Card boundaries. Caption times are microseconds; frame queries need the project frame rate. Review the complete clip for corrected words, phrasing, readability, animation rhythm and face clearance. A template source, standalone preview or successful binding is not proof of rendered captions. Re-read/reopen the saved project, and inspect the requested export before claiming completion. Report checks not performed rather than inventing a successful review.

## Import, visibility, translation and retries

- Import local media with Desktop `push_asset`; use `browse_assets` for status. For a transcription job, wait with `track_progress {action:"wait",target:"transcription",assetIds:"<asset id>"}`. Do not upload local media through an unrelated external path to bypass a limitation.
- `trigger_transcript` starts idle or failed transcription; then wait. One pending status is not a failure. Treat `no_audio` as successful analysis with no transcript. For an ongoing job, judge stuck only after observed waiting exceeds `max(5 minutes,min(60 minutes,2 × asset duration))`. A wait timeout/cancellation does not cancel transcription. Do not poll while a wait is pending or force-retry a running job through unsupported actions.
- If ready captions are empty, check whether the placed clip's source range actually contains spoken words. Do not blindly regenerate. Any necessary clip change must respect the user's requested edit.
- `enable`/`disable` controls the whole caption item; individual track visibility persists. `read_captions` includes hidden tracks, role, sourceTrackId and contentLanguageCodes. Restore a hidden language with its returned `showAction`; hide it with `{action:"track",trackId,visible:false}`. A null track languageCode does not mean missing text.
- Translate only into a requested language: `edit_captions {action:"translate",json:"{\"languageCode\":\"es\",\"mode\":\"bilingual\"}"}`. `bilingual` preserves the source; `translation` hides source captions. Optional `trackId` inside json selects the source track. Restore visibility without generating a translation; use `set_card_text` for translated wording corrections.
- For editorial speech cleanup, load `talking-head-guide`: `clean_script` handles mechanical fillers/pauses, while `read_script` → edit `timeline.md` → `apply_script` handles semantic edits. Verify the resulting script.
