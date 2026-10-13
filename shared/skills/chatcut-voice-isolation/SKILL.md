---
name: voice-isolation
description: |
  AI Voice Isolation (MossFormer2 speech enhancement) for video and audio items with spoken human voice.
  Cleans or isolates speech by suppressing non-voice sound around it. Picture is untouched —
  only the item's audio track is replaced with a cleaned derivative; clearing reverts to original.
  Triggers: "AI Voice Isolation", "voice isolation", "isolate voice", "clean up spoken audio",
  "clean up speech", "speech cleanup", "background noise", "noise reduction", "denoise speech",
  "dereverb", "de-reverb", "reduce reverb", "room echo", "echoey voice", "distant voice",
  "hiss", "hum", "fan noise", "room tone", "人声隔离", "AI 人声隔离", "人声净化",
  "背景噪音", "降噪", "噪声", "去混响", "混响重", "回声大", "空旷感",
  "人声不贴耳", "说话不清楚", "/voice-isolation"
user-invocable: true
---

# AI Voice Isolation (MossFormer2)

Clean or isolate spoken human voice on a video or audio item through Desktop's
native AI Voice Isolation route. The source asset is never modified —
the item's internal `denoisedAudioAssetId` is pointed at a cleaned derivative, exactly
like the editor's manual AI Voice Isolation. Playback and export pick it up automatically.

## When to Use

- User wants cleaner or more isolated spoken voice.
- User complains about hiss, hum, fan/AC noise, or room tone **around speech**.
- User asks to reduce room echo / reverb / reverberation / echoey or distant speech
  **on a spoken-voice clip**. Treat 去混响 / 混响重 / 回声大 / 空旷感 / 人声不贴耳
  as an AI Voice Isolation use case when there is spoken human voice.
- A talking-head / interview / voiceover clip needs cleaner speech before export.
- User asks to undo voice isolation → use the `clear` action.

**Do NOT use** for music, sound-effect items, ambience, or clips where there is no spoken
human voice. MossFormer2 is a speech-enhancement model — it suppresses everything
_except_ speech. On a clip with no voice (e.g. action footage, ambient nature sounds,
ping-pong in a noisy factory) it will distort or silence the audio because it has no
speech signal to preserve. If the user's request is to reduce or separate non-speech
background sounds, or to dereverb music / ambience / SFX, tell them ChatCut does not
have a suitable tool for that.

Call `isolate_voice` with
`action="apply"`, `itemId`, and `sourceAssetId`, but no
`filePath`. The editor will run the same AI Voice Isolation pipeline as the manual UI.

If the native route is unavailable, tell the user to apply it manually in the editor:
Library → Audio FX → AI Voice Isolation → drag onto the clip.

## Workflow (apply)

### Step 1 — Confirm the clip has spoken human voice

```text
preview_timeline, then inspect_item
```

Check the target item. Signs of speech: transcription markers, speaker labels, or the user
explicitly describing it as a talking-head / interview / voiceover. If you cannot confirm
speech is present and the content sounds like it could be non-speech (action footage,
ambience, music, etc.), **ask the user first** before processing.

A timeline line showing `voice-isolated=<n>` means AI Voice Isolation is already active on
that item.

### Step 2 — Apply through Desktop

```ts
isolate_voice({
  action: "apply",
  itemId: "<item id from preview_timeline — prefix id is fine>",
  sourceAssetId: "<the item's assetId from inspect_item>",
  strength: 100,
});
```

If this succeeds, stop. If it fails because no capable editor is open, report the
limitation; do not try to run a cloud-sandbox binary from Desktop.

## Workflow (clear / revert)

```ts
isolate_voice({ action: "clear", itemId: "<item id>" });
```

## Notes

- **Full-asset processing**: Desktop processes the whole source so the cleaned track
  covers the item without a range-miss fallback to the original.
- **Picture is preserved** for video items — only audio is swapped.
- **Native disk cache**: Desktop runs MossFormer2 through flux and keeps
  both the native inference cache and the generated derivative on disk. Manual
  and Agent requests reuse the same cache identity.
