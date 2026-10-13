---
name: voice
description: |
  Text-to-Speech (TTS), voice cloning, voiceover, narration placement/sync, and custom sound effects (SFX) generator. Use when the user wants generated speech from text, wants to clone a consented voice from uploaded reference audio, wants to correct a misspoken word or short phrase in recorded speech, wants to add/replace/align narration or voiceover for an existing video/timeline, wants to keep existing voiceover synced after visual retiming edits, needs voice audition/selection, or explicitly wants a newly generated/custom sound effect that is not available in the Sound Effects library.
user-invocable: true
---

# Voice & Sound Effects Generator

Generate voiceovers (TTS) and sound effects. For TTS, choose a concrete
provider and voice before calling `submit_voice`.

## When to Use

- Generate voiceover/narration from text
- Create text-to-speech audio for videos
- Add, replace, or redo narration/voiceover for an existing video, timeline,
  screen recording, slide animation, product demo, B-roll edit, MG explainer, or
  other visual sequence
- Keep existing narration/voiceover aligned after trimming, speeding up, slowing
  down, moving, reordering, or replacing the visuals it describes
- Offer and audition TTS voice choices when the user has not picked a concrete voice
- Clone the user's own or explicitly authorized voice
- Correct a real misspoken word or short phrase with the authorized speaker's
  cloned voice while preserving picture and downstream timing
- Generate custom sound effects from text descriptions only after checking the Sound Effects library first

## TTS (Text-to-Speech)

If the user wants to correct a word or short phrase that was actually spoken
incorrectly in existing recorded speech, read
[references/fix-spoken-mistakes.md](references/fix-spoken-mistakes.md) before
editing or generating. That workflow preserves the picture and protects later
timing while replacing only the faulty sound. Do not use synthesized speech
when the recording is already correct and only its transcript is wrong; fix
the transcript instead. Use the ordinary narration path for a full rewrite or
complete new voiceover.

If the current request has an existing visual target and the user wants
narration, voiceover, dubbing, or replacement speech for that target, read
[references/video-sync.md](references/video-sync.md) before drafting new
narration, using existing narration text to generate TTS, or placing audio. Do
this even when the user did not explicitly say "sync" or "match the visuals";
the existence of a visual target means narration timing and meaning may need to
follow on-screen content. Use the normal standalone TTS path only when there is
no visual target or the user just wants an audio asset from text.

Also read [references/video-sync.md](references/video-sync.md) when the timeline
already has narration/voiceover and the user asks to change the visuals while
keeping that voiceover aligned. This is a sync maintenance task even if no new
TTS is needed.

Use `submit_voice` to create a TTS audio asset. The current MCP tool contract is:

- `provider` is required. Use `doubao` for Chinese or Japanese narration and
  `elevenlabs` for English or multilingual narration.
- `voiceId` is required and provider-specific. Do not mix catalogs.
- `submit_voice` creates an audio asset only. Timeline placement, replacement,
  trimming, and alignment happen later with timeline tools.
- For standalone narration, make one `submit_voice` call by default even when
  the text is long, so the user receives one continuous audio asset. Split into
  multiple calls only when the user explicitly requests separate clips or when
  a visual workflow requires independently timed or placed voice clips, such as
  storyboard beats or scene-level ad segments. Length alone is not a reason to
  pre-split the narration.
- For Doubao, `speedRatio`, `loudnessRatio`, `pitch`, `emotion`,
  `emotionScale`, `performancePrompt`, `explicitLanguage`, and `explicitDialect` are supported
  knobs, but not every voice supports every expressive control. Use the
  selected official entry returned by `manage_voice action="list"` as the
  authority.
- For ElevenLabs, `modelId`, `speed`, and `stability` are the supported voice
  knobs. For `eleven_v3`, inline audio tags are available for expressive
  delivery such as emotion, tone, nonverbal cues, accent hints, pauses, or
  local pacing.

### Japanese narration

For Japanese speech (including a Chinese conversation asking for Japanese),
call `manage_voice action="list" voiceType="all" language="ja"` and set
`locale` to the conversation language. Use the returned Japanese audition
`previewUrl`/`sampleUrl` verbatim; `sampleLanguage` identifies the language
actually spoken in that sample. Do not use `other` for Japanese or relabel a
Chinese/English sample as a Japanese audition. Existing cloned voices can have
samples in another language; keep their original sample language clear.
After the user selects an official Japanese voice, submit with the returned
provider/voiceId and `explicitLanguage:"ja"`. Keep existing voice names.

### Keep voice providers private

Doubao, ElevenLabs, Fish Audio, their model names, and other provider identity
are internal implementation details. Never expose or attribute them in
user-facing replies, progress updates, voice recommendations, audition cards,
clone instructions, success summaries, or errors. Use ChatCut product language
instead:

- Call curated catalog voices `official voices` / `官方音色`.
- Call saved custom voices `cloned voices` / `克隆音色`, `My Voices` /
  `我的音色`, or use the voice's user-visible saved name.
- Describe status and failures at the ChatCut feature level. If a tool or
  provider error contains a provider name, model name, provider voice id, or
  provider URL, preserve the actionable meaning but remove those details
  before replying.

Provider names and provider-specific ids remain valid only in internal tool
arguments, tool-result interpretation, and these implementation instructions.
Do not copy them from tool output into visible UI metadata or prose.

Official voice controls come from `manage_voice action="list"`:

- Call it for the target narration language and the user's visible locale.
  Treat each returned `(provider, voiceId, name, summary, sampleUrl,
capabilities)` tuple as atomic.
- Use only fields in that entry's `capabilities.supportedControls`; never infer
  capability support from a remembered voice name or family.
- Controls are not guarantees of a specific acting style. Use the returned
  tags and sample to pick a naturally suitable voice, then use supported
  controls for moderate delivery changes.
- For entries that advertise `audioTags`, inline audio tags are available when
  the user asks for expressive delivery such as emotion, tone, nonverbal cues,
  accent hints, or local pacing. Official examples fit these useful TTS
  categories:
- Emotion/tone tags include `[happy]`, `[sad]`, `[angry]`, `[excited]`,
  `[curious]`, `[sarcastic]`, `[crying]`, `[annoyed]`, `[appalled]`,
  `[thoughtful]`, `[surprised]`, and `[mischievously]`; vocal delivery and
  nonverbal cue tags such as `[whispers]`, `[laughs]`, `[sighs]`, `[exhales]`,
  `[inhales deeply]`, `[clears throat]`, `[snorts]`, `[swallows]`,
  `[wheezing]`, and `[coughs]`;
  pacing/pause/local speed tags such as `[slowly]`, `[pause]`,
  `[short pause]`, `[long pause]`, `[rushed]`, and `[drawn out]`; and
  accent/special-performance tags such as
  `[strong X accent]`, for example `[strong French accent]`, plus `[sings]`,
  `[singing]`, `[woo]`, and `[pirate voice]`. Official examples are
  non-exhaustive; similar auditory tags can be tried when the user explicitly
  asks for that delivery and the tag describes how the voice should sound, not
  a visual action. Write tags directly in `text`, close to the short phrase
  they should affect. Treat tags as local guidance, not paragraph-wide controls.
- For pauses and pacing, use punctuation, text structure,
  shorter generated segments, or local audio tags such as `[short pause]` and
  `[slowly]` when needed.

```ts
// English / multilingual via ElevenLabs
submit_voice({
  provider: "elevenlabs",
  text: "Hello world",
  voiceId: "peter",
});

// Chinese via Doubao
submit_voice({
  provider: "doubao",
  text: "你好世界",
  voiceId: "liuchang",
});

// With speed adjustment (Doubao only)
submit_voice({
  provider: "doubao",
  text: "这是一段稍快的中文旁白。",
  voiceId: "liuchang",
  speedRatio: 1.5,
});

// With expressive Doubao controls
submit_voice({
  provider: "doubao",
  text: "这次事故提醒我们，安全永远不能侥幸。",
  voiceId: "liuchang",
  emotion: "sad",
  emotionScale: 3,
  performancePrompt: "痛心但克制，语速稍慢，像新闻专题旁白",
  pitch: -1,
  speedRatio: 0.92,
});

// With ElevenLabs delivery controls
submit_voice({
  provider: "elevenlabs",
  text: "The launch changed how teams plan their daily work.",
  voiceId: "peter",
  speed: 0.95,
  stability: 0.4,
});
```

## Cloned Voices in ChatCut Desktop

Before offering voices for a TTS request that does not name a concrete voice,
call `manage_voice` with `action:"list"` and `voiceType:"all"`. Build one
audition surface from the returned normalized candidates, keeping ready cloned
voices first and matching official voices after them. It is fine to infer likely
official voice qualities from the script, but never drop the user's ready
cloned voices because they lack official catalog tags.

A request to narrate in the user's own voice (for example "my own voice", "my
cloned voice", or a workflow that clones when no cloned voice is ready) is a
concrete source choice, not a request for official options. Audition only the
user's ready cloned voices (the voice picker adds its own clone card), or take
the clone route below directly when none is ready. Offer official voices only
if the user declines cloning or asks for them. Cloned-voice narration is
synthesized from text and can use a language the speaker never recorded, so a
narration language the user cannot speak is a reason to use their cloned
voice, never a reason to switch to official voices.

When the user has already supplied or identified usable local audio or video in the current
project for this cloning request, do not open the native flow and do not ask
them to select or upload the same source again. Resolve the source asset,
call `manage_voice` with `voiceType:"custom"` and
`action:"check-create-access"`, then collect only missing voice name, preview
text, and explicit authorization in an Agent widget. After authorization, call
`manage_voice voiceType:"custom" action:"clone"` with that audio or video asset id.
Desktop extracts the video's complete default audio track locally and uploads
only audio. Pass video directly; do not extract, convert, or import another
audio asset yourself. Detached timeline audio still references its original
video asset, so use that asset id. Timeline trims are not applied. The reference
audio must be 10–180 seconds and at most 25 MiB after extraction; this size limit
does not apply to the original video. A video without an audio track or a
reference outside these limits cannot be cloned; do not silently truncate it.

When the user has not supplied a usable reference, do not collect the
recording, name, preview copy, or authorization in chat. Explain briefly that
ChatCut will open the native flow, then emit exactly one atomic tag on its own
line:

```html
<clone-voice />
```

Immediately after the tag, add one short, localized sentence saying that once
they save the voice, it appears in the message box, and sending that message
lets the Agent continue the request. For example: `保存后音色会放进输入框，直接发送，我就继续。`
/ `Once you save it, the voice appears in the message box. Send it and I'll
continue.` Then stop and wait for the user's next message.

On this no-reference path, the Desktop dialog owns recording/upload, the
10-second to 3-minute validation, name, editable preview text, authorization,
entitlement checks, cloning, original-versus-cloned playback, retry, and
applying the selected voice back to the composer. Do not continue to clone
through `manage_voice` after emitting the tag. If the user closes the dialog,
wait for their next message.

When the user saves, Desktop puts the cloned-voice attachment and the localized
equivalent of `Continue generating with this voice.` into the message box. The
sentence follows the app language, so treat the attached voice, not its
wording, as the signal that cloning finished.

When a cloned-voice attachment is present in the request, follow its hidden
context exactly. First call `manage_voice` with `voiceType:"custom"`,
`action:"apply"`, and the attached ChatCut `customVoiceId` to confirm access, then call
`submit_voice` with `provider:"fish-audio"` and that same ChatCut
`customVoiceId` as `voiceId`. Never substitute a provider model id and never
expose the provider id.

For Fish Audio custom-voice synthesis, natural-language cues in square brackets
can guide a local phrase, for example `[whispering softly]`, `[excited]`,
`[calm and reassuring]`, or `[short pause]`. Put a cue immediately before the
text it should affect, keep it audible rather than visual, and use it only when
the user asks for expressive delivery. Treat it as guidance, not a guaranteed
exact performance.

## Voice Audition Before Generation

When the user needs TTS and has not already chosen a concrete preset, treat
broad words like "middle-aged male", "warm female", or "professional" as
requirements for filtering candidate voices.

Before recommending, rendering, or submitting a TTS voice option, use the
current `manage_voice action="list" voiceType="all"` result. It is the live
catalog shared with ChatCut Web, Desktop, and published plugins. Do not create
voice options from memory, translated names, filenames, or broad descriptions.

First determine two separate languages:

- User conversation language: the language the user used to talk to you. Use
  this for the surrounding reply, `form-visual label`, `visual-option name`,
  and `summary`.
- Target narration language: the language of the text being synthesized. Use
  this only to choose provider and voice catalog.

For the voice audition widget, set `submit_label` to a short submit action in
the user conversation language, not the target narration language. For example:
English users see `submit_label="Submit"`, Chinese users see
`submit_label="提交"`, and Spanish users see `submit_label="Enviar"`.

"help me generate ... voice over in Chinese" is an English conversation asking
for Chinese narration, so the audition widget copy stays in English while the
voice candidates come from Doubao.

Instead:

1. Call `manage_voice action="list" voiceType="all"` with the target narration
   `language`, user conversation `locale`, and explicit requirements such as
   gender, age, tone, and use case.
2. If no preset matches all explicit requirements, say there is no exact match
   and offer the closest supported presets with a clear caveat.
3. Keep returned ready custom voices with previews first, followed by 2-4
   matching returned official voices.
4. Load `widget-forms`. In Codex, call `ask_followup_questions` with voice
   options and audio samples. In Claude Code, render the recipe's combined
   voice cards and resolve each returned `sampleMediaKey` (for example `voice/<voiceId>/ja`) through
   `${CLAUDE_PLUGIN_ROOT}/assets/widget-media/manifest.json`; use a label-only
   card when the key is absent and never use or process the original sample URL.
5. Wait for the user to choose.
6. For a selected existing voice, call `submit_voice` with the selected tuple's
   `provider` and `voiceId`
   verbatim.

For Codex audition options, keep each entry's type, submission id, display
label, `previewUrl`, and `summary` tied to the same `manage_voice` tuple. Pass
each returned `previewUrl` verbatim as `audioUrl`: never prepend an inferred S3,
CDN, editor, localhost, or production base URL, and never reconstruct an
absolute URL from a filename pattern. For every host, use the returned localized
names and summaries. The target narration language filters the catalog; the
conversation locale controls visible copy. After the user submits, map the
submitted display name back to the provider/voice tuple from the same candidate
list.

In Claude Code specifically, use the provider-neutral localized display name as
the Elicitation `data-value` and keep the provider voice id only in the
label-to-tuple map held in context. Use an ephemeral DOM audio key for playback,
not the provider id. After the user presses Enter and the host-generated answer
line appears, map the visible name back to the returned provider/voice tuple and
continue without another confirmation.

English request for Chinese narration:

```html
<widget submit_label="Submit">
  <form-visual
    id="voiceId"
    label="For Chinese voiceover, I recommend a few voices to try:"
    required="true"
  >
    <visual-option
      value="<returned voiceId>"
      name="<returned English name>"
      media="<returned sampleUrl>"
      aspect-ratio="16:5"
      summary="<returned English summary>"
    />
  </form-visual>
</widget>
```

Chinese request for Chinese narration:

```html
<widget submit_label="提交">
  <form-visual
    id="voiceId"
    label="我推荐这几个中文旁白音色，先试听一下："
    required="true"
  >
    <visual-option
      value="<returned voiceId>"
      name="<returned Chinese name>"
      media="<returned sampleUrl>"
      aspect-ratio="16:5"
      summary="<returned Chinese summary>"
    />
  </form-visual>
</widget>
```

## Sound Effects

For ordinary editing sound effects (SFX), do **not** generate first. Search the
built-in Sound Effects library before spending credits:

1. Call `browse_library` with `category:"sound-effects"` and a query such as
   `"whoosh"`, `"camera shutter"`, `"notification"`, `"censor beep"`, or
   `"record scratch"`.
2. Inspect the returned `library:sound:<id>`.
3. The current Desktop Memory `edit_item` cannot import a Library sound id. Do
   not pass that id to `edit_item` or report it as placed. If the user wants the
   catalog sound on the timeline, report this tool-surface limitation.

```ts
mcp__core__browse_library({
  category: "sound-effects",
  query: "short whoosh transition",
});
```

Only generate sound effects from text descriptions with `submit_sound` when:

- The user explicitly asks for a generated/original/custom sound.
- The requested sound is too specific for the existing Sound Effects library.
- `browse_library({ category:"sound-effects", query })` returns no suitable
  match.

```ts
// Custom/generated sound effect after the library has no suitable match
submit_sound({ prompt: "A dog barking in the distance" });

// With custom duration (0.5-22 seconds)
submit_sound({
  prompt: "Thunder and heavy rain",
  durationSeconds: 15,
});

// High prompt adherence
submit_sound({
  prompt: "Sci-fi laser gun firing",
  promptInfluence: 0.8,
});
```

**Tips for better results:**

- Be specific: "A dog barking loudly" vs just "dog"
- Include context: "Footsteps on wooden floor in an empty room"
- Specify style: "Cinematic whoosh" or "8-bit game sound"

## Parameters

### TTS

| Field        | Description                            | Notes           |
| ------------ | -------------------------------------- | --------------- |
| `provider`   | TTS provider: `doubao` or `elevenlabs` | Required        |
| `text`       | Text to synthesize                     | Required        |
| `voiceId`    | Curated preset id or provider voice id | Required        |
| `speedRatio` | Speech speed                           | Doubao only     |
| `modelId`    | ElevenLabs model id                    | ElevenLabs only |
| `stability`  | ElevenLabs stability                   | ElevenLabs only |
| `speed`      | ElevenLabs speech speed                | ElevenLabs only |
| `name`       | Asset name                             | Optional        |

### Sound Effects

| Field             | Description       | Notes          |
| ----------------- | ----------------- | -------------- |
| `prompt`          | Sound description | Required       |
| `durationSeconds` | Duration          | 0.5-22 seconds |
| `promptInfluence` | Prompt adherence  | 0-1            |
| `name`            | Asset name        | Optional       |

## Voices

Use `manage_voice action="list" voiceType="all"` for the current unified voice
candidate list, localized display names, previews, and submission ids.

### Voice presets are provider-specific — do NOT mix them

Official voice ids are provider-specific. Always keep the returned `provider`
and `voiceId` together; mixing values from different catalog tuples will fail.

If you need a specific voice and a particular language:

- For any narration language, query the catalog with that `language` and use a
  returned provider/voice pair. Do not guess a raw provider id.

## Hard rules — what you must NOT do

1. Never use a voice preset name from a different provider.
2. Never submit TTS when the voice is only described broadly and the user has
   not confirmed a concrete preset.
3. Never recommend or render a TTS voice option before calling `manage_voice
action="list" voiceType="all"` for the current request.
4. Never claim stable age, regional accent, pronunciation dictionary, or exact
   duration controls; the current tool does not expose those as reliable fields.
5. Never replace original recorded speech with TTS unless the user asks.
6. Never expose Doubao, ElevenLabs, Fish Audio, provider model names,
   provider-specific ids, or provider URLs to the user. Use `official voice`
   and `cloned voice` product terminology, and sanitize provider details from
   visible errors and status messages.
