---
name: pixel-processing-gen
description: Create and refine Desktop video effects, masks, color treatments, and transitions by writing Flux/Blink HTML pixel processors directly. Use for entrance/exit animation of existing footage, chapter transitions, 入场动画、出场动画、章节转场、特效、滤镜、蒙版、调色、转场 and custom treatments of existing footage; use Motion Graphics for standalone generated graphics.
---

# Pixel processing

Write the effect or transition yourself as a local HTML entry and supporting files. Import it with `push_asset`, then apply it with `edit_item` when the user wants it on footage. This workflow runs authored code in Flux/Blink; it does not submit a generation job.

## Built-in Agent delegation

For a simple change to an existing exposed parameter, the main agent should act directly: change timeline property overrides for a placed instance, or inspect the asset and use `edit_asset` with `action:"update"` and `json.properties` to change asset defaults. Preserve the other property definitions and the same asset ID. Do not rewrite source fallbacks or delegate solely to change a default. When `delegate_task` is available, use it for new processor creation or changes to rendering/audio logic, animation or structure; delegate when unsure how to implement a code change. Pass `request: {action:"start", agent, name, task}`. Set `agent` to the requested `pixel-effect`, `pixel-transition`, `audio-effect`, or `audio-transition`, provide a descriptive `name`, and a self-contained `task` with the goal, media context, timing and controls. The specialist writes source, validates, decides whether visual review is needed, and calls its restricted `publish_output` tool. Start/revise/resume return `status:"started"` and a `taskId` immediately; this does not mean the asset is ready. Different assets run independently, including after the parent chat is interrupted. Use `track_progress({target:"subagent",action:"wait",taskIds:taskId})` once to obtain the final outcome before claiming completion or placing an asset. The call waits until completion, pause or failure; do not poll. `track_progress` with `action:"status"` checks without waiting and `delegate_task` with `action:"stop"` cancels only that task. Successful completion returns an already imported `assetId`. Use that ID for placement and verification; do not call `push_asset` again. It does not modify the timeline. Native probes do not replace review on representative footage or audio audition. A `status:"paused"` result preserves the source, original SDK session and asset placeholder. Decide whether further work is justified: call `delegate_task({request:{action:"resume",taskId,feedback}})` with a concrete correction plan, or `delegate_task({request:{action:"stop",taskId}})`. Ask the user when intent, tradeoffs or additional cost need their judgment. Do not blindly repeat resumptions. Never bypass a paused task with a direct `push_asset` or a duplicate start. External agents without this tool use the direct author/import workflow below.

For example, `delegate_task({request:{action:"start",agent:"pixel-transition", name:"Space reorganization", task:"<user goal, source context, timing and controls>"}})`. Assets shows creation, preview checking and import progress. Completion means the asset is imported; applying it to the timeline remains the parent agent’s responsibility.

External ACP agents do not receive this tool. When it is absent, write and verify the source directly using this skill.

## Choose the treatment

Choose the route from the user's intent before browsing:

- Ordinary polish, named presets and parameter adjustments: use built-ins. Search the relevant category/query directly; returned `use` instructions are sufficient to apply a match. Read detail only for missing information, not as a mandatory step for every candidate.
- A request to design a distinctive entrance, exit, or chapter transition is a creation task even if the user never says HTML or "custom". Use the live footage as the material for an original design; do not reduce it to a stock zoom plus fade simply because those are available. Load this skill, inspect representative footage and delegate creation when available. Existing-input entrance/exit animation is a pixel effect; connecting two shots is a pixel transition.
- A request merely to add a transition can still use a fitting built-in. Do not treat every mention of animation or "smooth" as a mandate to author code. Honor a named preset or an explicit request to reuse built-ins.

For zoom, portrait cutout, masks and LUTs, consult [built-in recipes](references/builtins.md). Segmentation should reuse native portrait cutout, not be reimplemented in HTML. For original design, start from the request and footage; catalog enumeration is not a required creative phase.

- A **pixel effect** transforms one live input. It can target a clip or a track range.
- A **pixel transition** combines two adjacent clips at a cut. It needs both endpoint item IDs and available source handles.
- A standalone scene without input footage belongs in the Motion Graphic workflow.

Before writing HTML, read [the HTML processor contract](references/html-contract.md). It includes minimal effect and transition entries. Extend them to the intended visual treatment, rather than substituting a pre-rendered video or unrelated overlay.

## Design intent

Before implementation, briefly state the intended viewer experience and how it serves the user’s request and available footage. Use this intent to guide composition, motion, timing, and the relationship between the inputs. Make these choices form a coherent whole; choose the visual language to suit the request, without assuming a preferred style or a required set of techniques.

Treat the first implementation as a draft. Compare rendered output with the stated intent, identify concrete gaps, and revise the source and validate again. Successful execution alone does not establish that the design works. When reference footage is unavailable, state that limitation rather than inventing observations about it.

## Source organization

Keep the processor **self-contained as a directory**, with a clear HTML entry and local dependencies. Prefer focused files when distinct responsibilities emerge, so the entry remains easy to read and individual concerns can be revised independently. Choose boundaries from the implementation rather than a fixed file list or file-count target. A small processor may remain in one file.

Keep related implementation together, make dependencies explicit through local imports, and avoid duplicating state or introducing abstractions only to split files. Validate and review through the entry after changes to any supporting file.

## Author, import, apply

The Agent working directory is `<project>.chatcutproject/workspace`. Write reusable effect source under `<project>.chatcutproject/assets/pixel-effect/` and transition source under `<project>.chatcutproject/assets/pixel-transition/`, using the actual open project path from the runtime context. Choose your own descriptive subdirectory and entry filename (for example `panel-fold/transition.html`); neither must be a UUID or `index.html`. Keep relative modules, styles, and other resources together, and avoid overwriting existing processors. These are authored source files, not the asset metadata JSON files managed by Project tools. `push_asset` generates the asset UUID independently and records the path without moving files. Do not create an asset UUID yourself or rename the directory after import. An `.html` entry must contain exactly one module script that default-exports `mount`. Use the source-organization guidance above for the entry and its supporting files.

```json
{
  "filePath": "/absolute/MyProject.chatcutproject/assets/pixel-effect/prism/effect.html",
  "type": "pixel-effect",
  "name": "Prism",
  "properties": [
    {
      "key": "strength",
      "label": "Strength",
      "type": "number",
      "defaultValue": 0.25,
      "min": 0,
      "max": 1,
      "step": 0.01
    }
  ]
}
```

Call `push_asset` with that object. Use `type: "pixel-transition"` for a transition. Desktop selects `{kind:"html"}` from the `.html` path and keeps it linked; width, height and duration are supplied by the target composition, not import parameters. Import runs native Flux validation before registering the asset. Check each returned result for success before using its asset ID. On validation failure, use the returned diagnostics to fix the source and retry `push_asset`; no asset is created for the failed entry.

Pixel effects can attach directly to visual items, including `motion-graphic` and `svg`, using `targetItemId`. A block effect processes the underlying track composite, so do not substitute it for an item effect merely because the item is a Motion Graphic. Effect-specific restrictions (such as AI Portrait Cutout requiring image/video) still apply.

For application, read the affected timeline with `preview_timeline` and inspect the relevant items. Use returned IDs, not guessed ones:

```text
edit_item({adds:[{type:"pixel-effect",assetId:"<asset-id>",targetItemId:"<clip-id>",propertyOverrides:{strength:0.35}}]})
edit_item({adds:[{type:"pixel-effect",assetId:"<asset-id>",trackId:"<track-id>",startFrame:90,durationFrames:60}]})
edit_item({adds:[{type:"pixel-transition",assetId:"<asset-id>",outgoingItemId:"<outgoing-id>",incomingItemId:"<incoming-id>",durationFrames:24}]})
```

A failed transition placement may require a shorter duration or more clip handles. Do not silently move unrelated clips. Importing a reusable asset alone is enough when the user only asks to create an effect.

## Properties and revisions

`asset.properties` is an array defining controls. Pixel processor property types are `number`, `boolean`, `color`, `select`, and `vec2`; do not use Motion Graphic-only property types. Resolved defaults plus the applied item's `propertyOverrides` arrive as `props` in `update({props, revision})`. Read them there, with sensible fallbacks, and render using the latest values.

Use `edit_asset` to update the asset's property schema and `edit_item` for a particular instance's overrides. Edit the linked HTML and supporting files directly for code changes. Do not send HTML through `edit_asset.code` / `codeFile`, which follows the legacy TypeScript source-materialization path. Inspect the asset path before changing an existing asset, and preserve its runtime.

## Verify what the viewer sees

A successful import proves registration, not visual correctness. Apply the effect to representative footage and use the available timeline/asset frame preview tools to inspect the beginning, middle, and end; seek backward as well. For transitions, check that the endpoints exactly match outgoing and incoming frames without flashes or residual layers. Check both live-input motion and editable-property changes.

When native Flux validation is available, validate the matching HTML kind and path through `validation.validatePixelEffectCode` or `validation.validatePixelTransitionCode` with `runtime: {kind:"html"}`. This uses the native processor and deterministic probes; it does not replace visual review. Surface actual import/render errors, fix the source, and verify again. If native execution is unavailable, label browser-only previews as such rather than claiming the effect works in Desktop.

For the built-in processor sub-agent, decide whether the change needs visual review. For a simple change you can confidently assess without images, pass `skipVisualReviewReason` to `validate_output` explaining why. Basic native validation remains required. Otherwise omit the field to receive five rendered fixture frames and five unprocessed reference frames; request images when unsure. Do not claim visual review when skipped. Inspect these images before calling `publish_output` with `observations` to accept and import the result: compare the result to your stated design intent and the user’s request, explain which visible observations support your assessment, and identify any remaining gaps. Also verify that the requested treatment is visible, inputs are preserved as intended, and transition endpoints and intermediate frames are correct. If output is black, missing, or incorrect, repair the source and validate again. Only publish output you accept for delivery. With a current explicit visual-review skip, `publish_output` may omit observations. Source edits invalidate validation and require fresh review or an explicit skip. Fixture review does not replace checking the applied result on the user’s footage.

Assess motion and timing through continuous playback when available. Sampled frames support visual inspection but do not prove temporal quality; report what was actually observed and leave unverified aspects explicit.
