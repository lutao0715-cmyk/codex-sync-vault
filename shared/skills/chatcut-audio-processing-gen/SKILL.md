---
name: audio-processing-gen
description: Author custom Flux Desktop audio effects and audio transitions as local Web Audio JS/TS modules. Use for EQ, filters, saturation, delay, reverb and creative crossfades; music/voice generation and AI voice isolation use their own workflows.
---

# Audio processing generation

Write the processing module directly. This creates a reusable audio processor, not a backend generation job and not a generated music or speech clip.

First use `browse_library` when a built-in audio effect or transition matches the request. For custom processing, read [the audio runtime contract](references/audio-contract.md), then write a `.ts` or `.js` module in a durable project workspace. Audio processors do not use the HTML pixel runtime.

## Built-in Agent delegation

For a simple change to an existing exposed parameter, the main agent should act directly: change timeline property overrides for a placed instance, or inspect the asset and use `edit_asset` with `action:"update"` and `json.properties` to change asset defaults. Preserve the other property definitions and the same asset ID. Do not rewrite source fallbacks or delegate solely to change a default. When `delegate_task` is available, use it for new processor creation or changes to rendering/audio logic, animation or structure; delegate when unsure how to implement a code change. Pass `request: {action:"start", agent, name, task}`. Set `agent` to the requested `pixel-effect`, `pixel-transition`, `audio-effect`, or `audio-transition`, provide a descriptive `name`, and a self-contained `task` with the goal, media context, timing and controls. The specialist writes source, validates, and calls its restricted `publish_output` tool. Pixel specialists accept their latest rendered output in the publication observations unless review was explicitly skipped; audio specialists require the native synthetic export and may publish without visual observations. Synthetic audio validation is not an audition. Start/revise/resume return `status:"started"` and a `taskId` immediately; this does not mean the asset is ready. Different assets run independently, including after the parent chat is interrupted. Use `track_progress({target:"subagent",action:"wait",taskIds:taskId})` once to obtain the final outcome before claiming completion or placing an asset. The call waits until completion, pause or failure; do not poll. `track_progress` with `action:"status"` checks without waiting and `delegate_task` with `action:"stop"` cancels only that task. Successful completion returns an already imported `assetId`. Use that ID for placement and verification; do not call `push_asset` again. It does not modify the timeline. Native probes do not replace review on representative footage or audio audition. A `status:"paused"` result preserves the source, original SDK session and asset placeholder. Decide whether further work is justified: call `delegate_task({request:{action:"resume",taskId,feedback}})` with a concrete correction plan, or `delegate_task({request:{action:"stop",taskId}})`. Ask the user when intent, tradeoffs or additional cost need their judgment. Do not blindly repeat resumptions. Never bypass a paused task with a direct `push_asset` or a duplicate start. External agents without this tool use the direct author/import workflow below.

External ACP agents do not receive this tool. When it is absent, write and verify the source directly using this skill.

## Declare the asset kind

Call `push_asset` with an explicit `audio-effect` or `audio-transition` type. Desktop identifies the source format; do not supply runtime or ask it to infer the effect/transition kind.

```json
{
  "filePath": "/absolute/project-workspace/audio/telephone.ts",
  "type": "audio-effect",
  "name": "Telephone",
  "properties": [
    {
      "key": "cutoff",
      "label": "Low-pass cutoff (Hz)",
      "type": "number",
      "defaultValue": 3200,
      "min": 200,
      "max": 10000,
      "step": 10
    }
  ]
}
```

`properties` is an array; audio properties support `number`, `boolean`, and `select`. The module receives frozen resolved values as `properties`. Use asset defaults for reusable settings and applied-item overrides for instance settings. Keep linked source files available and edit them directly for revisions.

Check the returned import result before using the asset ID. Import creates a library asset; it does not attach a processor. Audio effects have an item, track, or master target and no independent timeline range. Audio transitions need adjacent audio-bearing clips, enough source handles, and an explicit duration.

Apply imported audio processors with `edit_item`. Audio effects accept exactly one target: `targetItemId` for audio/video, `trackId` for a track, or `target:"master"` for the timeline mix. Audio effects have no frame range. Audio transitions connect adjacent audio/video items on the same track using `outgoingItemId`, `incomingItemId`, and `durationFrames`. Use `propertyOverrides` for parameters. Updates/deletes require the attachment ID and exact `type`. Check the tool result and audition the affected audio before claiming completion.

```text
edit_item({adds:[{type:"audio-effect",assetId:"<asset-id>",targetItemId:"<audio-or-video-item-id>",propertyOverrides:{}}]})
edit_item({adds:[{type:"audio-transition",assetId:"<asset-id>",outgoingItemId:"<outgoing-id>",incomingItemId:"<incoming-id>",durationFrames:12}]})
```

## Verify by listening

Use representative speech or music and compare processed output to the original at matched loudness. Render through Flux's native audio export when available; a generic browser graph is only a preliminary check. Inspect the exported signal for non-finite samples, clipping, unexpected silence, clicks and excessive tail/latency. Listen to the result.

For transitions, export both the whole cut and a range beginning inside it. A mid-transition seek must begin at the correct mix, not restart a fade. Test the beginning/end of the clip and the actual output sample rate. Tails never extend the requested timeline/export range.

Report what was authored, whether it was imported/applied, and what was actually rendered or auditioned. Keep a clear distinction between code that looks plausible and a verified native result.
