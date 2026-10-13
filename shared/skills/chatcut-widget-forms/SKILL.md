---
name: widget-forms
description: Build native in-chat forms for the built-in ChatCut Desktop Agent and embedded ACP agents. Use for file uploads, structured input, and preview-based choices, including MG or Design Style image cards, voice auditions, and caption style previews.
---

# Widget Forms

### In-app screen recording

When the user wants to record a screen in ChatCut, emit `<record-screen/>` directly
in assistant text, outside a widget or code block, then end the reply. This is a
native action button, not a tool and not a form submit. The user's click selects
screen mode and opens the existing recorder. Explain that they choose the shared
surface and optional microphone/camera there; never claim capture started merely
because the button or picker is visible. Do not append another confirmation CTA.
After successful import, the host submits a follow-up with the recorded asset
references; verify those assets before continuing. Cancellation or save failure
is not completion. Use this tag only inside embedded ChatCut Desktop/Web chat;
external clients must guide the user to the timeline's screen recorder instead.

## Embedded ChatCut Desktop Runtime (highest priority)

When running inside ChatCut Desktop, as the built-in ChatCut Agent or an
embedded ACP agent:

- Choose the interaction protocol from the active host, not from whether the
  agent family is Codex or Claude Code.
- Write `<choices/>` and `<widget>...</widget>` directly in the assistant
  response. They are response text, not tool calls.
- Use `<choices/>` only for one text-only decision. Use `<widget>` for
  file uploads, structured input, or when seeing or hearing a candidate is
  part of the decision.
- Do not call `ask_followup_questions`, discover `visualize`, or call
  `visualize.show_widget`.
- Provider-specific form instructions below or in another skill apply only to
  standalone hosts and do not override this embedded route.
- Emit one interaction mechanism per reply, keep visible labels in the user's
  conversation language, then stop and wait for the submitted answer.

### Native `<widget>` tag syntax (embedded runtime only)

Six components. Five are self-closing `<form-xxx attr="..."/>`; `<form-visual>`
is a block tag. Only `id` is required (it becomes the answer key).

- `<form-single id="..." label="..." options="value|Label,value2|Label 2"/>` —
  single choice pills. An "Other" pill is auto-injected in the user's language;
  pass `allow_other="false"` only for closed sets.
- `<form-multi id="..." label="... (multi-select)" options="a,b,c"/>` — multi
  choice; the label must mark it as multi-select in the user's language.
- `<form-text id="..." label="..." placeholder="..."/>` — single-line input.
- `<form-textarea id="..." label="..." rows="3"/>` — multi-line input.
- `<form-files id="..." label="..." accept="video/*"/>` — upload tile grid. Digital-human portrait uploads additionally use `purpose="avatar-source"`; other uploads omit it.
- `<form-visual id="..." question="...">` … `</form-visual>` — visual card
  grid. **Block tag, never self-closing, and it has no `options` attribute.**
  Each card is a nested child:
  `<visual-option value="..." name="..." media="https://..."/>`.
  For Design Style catalog cards write **only**
  `<visual-option preset-id="..."/>` using real preset ids returned by
  `manage_design_style action="list_presets"` — the host fills in name,
  thumbnail, and aspect ratio from the catalog. Do not invent display names or
  copy thumbnail URLs for catalog presets. MG style discovery follows the MG
  skill's `manage_design_style list_presets` workflow, using returned catalog
  images and exact Design Style UUIDs. Do not replace the visual decision with
  `<choices/>`, `<form-single>`, `<form-multi>`, or invented prose directions.
  Retry unavailable references while retaining their IDs; report an unresolved
  failure instead of fabricating choices or claiming the catalog was read.
  For AI-avatar catalog cards write **only**
  `<visual-option avatar-id="..."/>` using exact identity ids returned by
  `manage_avatar action="catalog"` — the host fills in name, preview image,
  aspect ratio, and submitted value. Do not add `value`, `name`, `media`, or
  `aspect-ratio` to an `avatar-id` option.

### Project image and video candidates (embedded runtime only)

For images or videos already imported into the current project's media library,
use `<visual-option asset-id="FULL_ASSET_ID"/>` inside `<form-visual>`. Obtain
exact IDs from project/tool results; do not invent IDs or add `value`, `name`,
`media`, `preset-id`, or `avatar-id`. The host resolves the filename and thumbnail.
Image and video cards share a 16:9 frame, fitting portrait and square sources
without cropping. Video cards show a poster and duration, play muted on hover,
and stop/reset to the poster when the pointer leaves or enlargement opens.
The Enlarge button appears on hover or keyboard focus and opens the media library's
shared preview without selecting or submitting the card. Video previews include
playback, seeking, volume, and the existing transcript sidebar when available.
Submission includes the selected asset's real ID and image/video category.
Unavailable images and removed/foreign assets cannot be selected; a video poster
failure still allows opening the video player. Import candidates before presenting them.

```html
<widget>
  <form-visual id="broll" question="Which shot fits this scene?">
    <visual-option asset-id="FULL_IMAGE_OR_VIDEO_ASSET_ID_FROM_PROJECT" />
  </form-visual>
</widget>
```

For a visual question that accepts several images/videos or references, set
`multiple="true"` on `<form-visual>` and explicitly say multi-select in the
question's language. Merely writing "multi-select" in the title does not enable
it. Each selected card can be toggled independently; submission includes every
selected asset ID. Omit `multiple` (or use `multiple="false"`) for one choice.
Avatar, voice-library, Design Style catalog, and caption-style pickers remain
single-choice. Do not mark those questions as multi-select.

```html
<form-visual
  id="broll"
  question="选择使用的 B-roll 画面（支持多选）"
  multiple="true"
>
  <visual-option asset-id="FIRST_ASSET_ID_FROM_PROJECT" />
  <visual-option asset-id="SECOND_ASSET_ID_FROM_PROJECT" />
</form-visual>
```

Images and videos can be mixed in one group. Existing Design Style image cards
also support enlargement. This native `asset-id` contract does not extend the
external `ask_followup_questions` schema.

Use `default="..."` to prefill `<form-text>` or `<form-textarea>`. Before
putting dynamic text in any native component attribute, XML-escape it once:
replace `&` first, then encode `"`, `'`, `<`, and `>` as `&quot;`, `&#39;`,
`&lt;`, and `&gt;`. Do not use backslash escapes. The host decodes this attribute
layer before the component renderer performs final HTML escaping.

### Caption style previews (embedded runtime only)

When asking the user to choose a caption style, use visual cards instead of
text-only choices. Call `edit_captions action="template"` without
`templatePreset` / `preset` to list the built-ins for the caption source language.
When captions do not exist yet, transcript language is unknown, or sources use
different languages, pass the known target in the tool's `json`, for example
`{"languageCode":"zh"}` or `{"languageCode":"en"}`. Catalog choice follows the
caption language, not the interface or conversation language. If the target is
unknown, determine it first; do not treat the no-language general catalog as
Chinese recommendations. Use only that query's returned ids in `<visual-option caption-preset-id="..."/>`. The host renders a
current caption and its adjacent page, preserving actual pagination, subtitle language and token timing. It uses sample text only when captions are unavailable. Set `caption-language="en"` on `<form-visual>` (or the target language code): translated captions follow the translation language, not the media or interface language. For bilingual captions, offer separate, clearly labeled questions for each language and apply each selection to that source. Previews use shared caption layout and the preset's font, colors and animation. The background reuses the media-library checkerboard.
Visible cards automatically loop through the pages; offscreen or hidden cards pause. No preview video
assets or agent-authored `media`, `name`, `value`, or `aspect-ratio` are needed.
Only built-in caption presets are supported, not saved-style UUIDs or Design
Style `preset-id` values.

```text
<widget>
  <form-visual id="caption_preset" label="Choose an English caption style" caption-language="en" required="true">
    <visual-option caption-preset-id="persona"/>
    <visual-option caption-preset-id="bubble-pop"/>
    <visual-option caption-preset-id="submagic"/>
  </form-visual>
</widget>
```

These ids illustrate syntax; choose actual candidates from the tool's list.
Previewing does not modify the project. After submission, apply the stable id
from the submitted selection context through `edit_captions action="template"`, preserving caption
geometry, pagination limits, and the intended source scope. The preview zooms the caption band for comparison; highlighted captions retain real token timing and non-highlighted pages change about once per second.
This native protocol does not extend the standalone MCP-host forms below.

Do not write `<form-actions/>` — the host auto-injects a localized submit
button. Leave `submit_label` unset too, unless another skill explicitly
instructs otherwise (the `voice` audition flow sets it).

Host scope: the `ask_followup_questions` MCP-App widget below renders in hosts that support ChatCut form widgets (Codex). Claude Code does not render MCP-App widgets — use the Claude Code recipe below for the same moments with the same content. Single-question fields and user-language labels apply to every host. The no-file-upload restriction below applies to standalone Codex forms, not the embedded ChatCut Desktop runtime, which supports `<form-files>`.

## Claude Code Runtime (verified 2026-07-15)

Hard boundary: Claude Code does not render ChatCut MCP-App results. Never call
`ask_followup_questions` in this runtime. Use the host-native `show_widget` tool
on the `visualize` server:

1. Discover `visualize.show_widget`, then load its `read_me` with the
   `elicitation` module for the current desktop platform. Follow the current
   contract rather than examples remembered from an earlier session. Load it
   once and reuse it for the rest of the session; do not rediscover or reread it
   for each form. Read
   [references/elicit-recipes.md](references/elicit-recipes.md) only when the
   form contains visual or voice media cards. A plain single/multi/text form
   needs only the current `read_me` contract.
2. Infer first from the conversation, project state, and attachments. Ask only
   for information that is both necessary for the next step and not already
   known. Then render exactly one host-wired `<form class="elicit">` using the canonical header, body,
   group, footer, and fixed
   chrome from `read_me`. Put all related questions, media previews, and the
   single submit action in this one widget; never render a preview widget plus a
   second question UI. Claude Desktop already draws the outer `show_widget`
   frame, so keep the required `.elicit` structure but flatten only its visual
   wrapper with
   `style="border:0; border-radius:0; box-shadow:none; background:transparent"`.
   Do not remove or rename the form, header, body, or footer classes; they remain
   required for answer collection and submission.
3. Map single/multi choices to
   `.elicit-pills[data-name][data-multi]` containing
   `.elicit-pill[data-value]`; use the documented Elicitation controls for
   text and Other values. For an off-list answer, use exactly one
   `.elicit-pill[data-other]` and one adjacent `.elicit-other[data-for]`;
   `data-for` must exactly match the pill group's `data-name`. Visual, voice,
   cards remain selectable `.elicit-pill` controls with clean `data-value`
   attributes. Ordinary and visual choices use buttons. A voice
   choice uses one non-button `.elicit-pill` card that directly contains its
   title, description, and native audio player; current Claude Desktop wires
   selection by the `.elicit-pill` class rather than the element tag.
4. Submit only through `<button type="button"
class="elicit-submit">...</button>`. In Claude Code Desktop this fills the
   composed answer into the user's prompt box; it does not press Send. Use an
   honest fill-oriented action label such as "Fill editing brief".
   Never claim "sent" before that user message appears in chat. Stop the current
   turn and wait for the user to send the filled prompt.
5. Build canonical option tuples before reading media or writing HTML. This is
   a hard preflight gate; do not call `show_widget` until every visible media
   option has an authoritative `(id, display label, description/tags)` source:
   - MG style cards: reuse the active MG skill's shortlist and catalog previews,
     keeping each Design Style UUID mapped to its title. Do not restart discovery
     with `list_presets` when rendering these choices.
   - Explicit Design Style catalog cards: call `manage_design_style` with
     `action: "list_presets"` and `locale` matching the conversation language.
     Choose from that result and copy each returned `id` and `name` exactly.
     Never derive, translate, shorten, or improve a preset name from its image.
   - Voice cards: load the `voice` skill and call `manage_voice` with
     `action:"list"`, normally `voiceType:"all"`, plus the target narration
     language and conversation locale. Choose one returned tuple per card. Keep
     `provider` + `voiceId` for official voices, or `customVoiceId` + the exact
     `previewUrl` for custom voices, together with the tuple's type, localized
     name, and summary. Never create a voice name from broad traits or a
     filename.
     If either authoritative source is unavailable or times out, do not fabricate
     options and do not render a misleading form. Report the catalog problem
     concisely and retry only after the source is available.
6. Read `${CLAUDE_PLUGIN_ROOT}/assets/widget-media/manifest.json` only after the
   canonical tuples exist. The manifest is a media resolver, not a naming
   catalog. Resolve MG styles with `entries["design-style/<UUID>"]`, preserving the
   exact Design Style UUID; never substitute a similarly named preset. Resolve catalog
   presets with `design-style/<presetId>` and official voices with the returned
   `sampleMediaKey` (such as `voice/<voiceId>` or `voice/<voiceId>/ja`),
   then concatenate the manifest
   `baseUrl` and entry `path`. For a custom voice only, use the exact
   `previewUrl` returned in its `manage_voice` tuple. Ignore every other
   caller-provided S3, CloudFront, `app.chatcut.io`, relative, or non-manifest
   URL. If approved media is absent, render that exact authoritative label
   without media in the same form. Never download, resize, transcode,
   base64-encode, print, or save media or build intermediate HTML/JSON files at
   runtime.
7. Keep visual sets focused: show 3 strong choices by default and expand toward
   6 only when the user asks to browse more broadly or the decision genuinely
   needs that range. Keep the HTML payload small; remote media bytes must never
   enter the prompt or widget arguments.
8. Write zero event handlers and zero custom scripts. Voice audition uses a
   single non-button `.elicit-pill` card with its native `<audio controls>`
   nested directly inside. Clicking the card or its player selects that voice
   through the host's delegated `.elicit-pill` handler, while playback remains
   browser-native. Do not wrap the player in a `<button>` and do not create a
   separate selector card above it. Do not use
   `sendPrompt(...)`: live testing shows that it also only fills Claude Code
   Desktop's prompt box despite its read-me wording.
9. Do not add file input to an Elicitation form: one file group currently breaks
   handoff for every answer. Ask for missing source media outside the form by
   telling the user to drag it into the chat input, then import the readable
   local path with Desktop's `push_asset` tool.
10. In the structured collection scenarios covered by this skill, do not replace
    the combined form with `AskUserQuestion`; that modal is more interruptive and
    loses the single multi-question intake experience. This does not restrict
    normal `AskUserQuestion` use in unrelated workflows. If `show_widget` is
    genuinely unavailable, ask concisely in ordinary chat.

For media forms, minimize first-render latency by starting all independent
preparation together after this skill loads: load the current Elicitation
`read_me`, read this skill's media recipe and manifest, and fetch only the
authoritative catalogs actually needed by the form. Call
`manage_voice action="list"` only for voice cards; call `list_presets` only for
explicit catalog-preset pickers. MG reference choices reuse the active MG
workflow's fetched shortlist and details.
Do not serialize independent reads, inspect unrelated skills, probe media URLs,
or create intermediate files. Reuse all loaded local contracts and catalogs for
later forms in the same session. Once the required option data is available,
`show_widget` is the final call.

Claude Elicitation file attachments are not ChatCut project imports. When the
attachment is available as a readable local path, use Desktop's `push_asset`.

Use user-language readable copy for `data-name` and `data-value`; the host puts
those strings directly into the filled answer line. Keep preset ids and voice
ids out of those attributes, and retain a label-to-id map from the
tool results in context. The host formats the answer as `<header> details —
<data-name>: <value> · ...`, with comma-separated multi-select values. Once that
line appears as a user message, map each visible label back to the internal id
from the candidate list and continue without asking the same questions again.

Immediately before `show_widget`, audit every media card in both directions:
the visible label must map to exactly one authoritative tuple. Its media must
resolve from that tuple's manifest key for Design Styles and official voices,
or equal that tuple's exact `previewUrl` for a custom voice. A label copied from
a different id, an invented alias, a shortened official name, or media chosen
before the catalog lookup is a failed preflight. Fix the tuple instead of
rendering it.

## Codex Runtime

Hard boundary: use the ChatCut MCP Apps form tool in Codex. Do not copy Claude
Code's Elicitation HTML or `show_widget` recipe into a Codex conversation, and
do **not** output raw ChatCut native `<widget>...</widget>` HTML; Codex cannot
render that editor-only protocol.

### Runtime Rule

Call `ask_followup_questions`. This is the Codex/external-MCP equivalent of the
native ChatCut widget form protocol.

Plan the whole questionnaire before calling the tool. Send one final form, not a
trial form followed by a corrected form. The tool supports at most 12 fields; if
the user asks for more questions, merge related prompts into combined fields
before the first call.

After calling `ask_followup_questions`, stop the turn and wait for the submitted
answer to appear in chat. Do not apply a choice, create assets, or continue
planning from a recommendation until the user's selection is present in the
conversation.

### Supported Field Mapping

Build a `fields` array. Write every visible string in the user's conversation
language.

Fields are required by default. Set `required: false` only when the user may
genuinely skip that field; never make a blocker optional merely to let the form
submit. If the user selects an explicit Other option, its text entry must also be
filled before submission.

- Native `<form-single>` -> `{ type: "single", variant: "default" }`
- Native `<form-multi>` -> `{ type: "multi", variant: "default" }`
- Native `<form-text>` / `<form-textarea>` -> `{ type: "text" }`
- Native `<form-visual>` -> `{ type: "single", variant: "visual" }`
- Voice audition cards -> `{ type: "single", variant: "voice" }`

### Form Copy Tone

For form-level text (`title`, `prompt`, `fields[].label`, `submitLabel`, and
`messagePrefix`), write like ChatCut is a capable video-making partner inviting
the user to describe what they want, not like a rigid survey.

Aim for:

- Warm, open-ended, and action-oriented. The copy should imply "choose the
  closest video need or just tell me your idea; we can figure it out together."
- Short and scannable. Use one natural sentence for `prompt` and concise
  question labels.
- Honest capability framing. ChatCut can help with many video workflows, but do
  not claim unsupported abilities or guarantee a result before inputs are known.
- The user's language and local product terms. Keep "ChatCut", "B-roll",
  "Motion Graphics", "MG 动画", model/product names, and platform names in their
  established forms.
- User-facing creative wording. For early planning or creative-intake forms,
  prefer natural terms such as idea, direction, plan, story, shot list, audience,
  mood, or video need over internal production-document language.

Avoid stiff labels such as "Select video type" or "Please choose the video type
for this project" unless the host has no room for warmer copy.

Do not include file-upload questions in Codex forms. If a task actually needs
source media and the project/chat does not already have it, ask the user
separately to upload files through the Codex composer Add files flow or directly
in the ChatCut editor. File upload is not a default prerequisite for every
questionnaire; only ask for it when the next editing step depends on missing
media.

For choice fields:

- Use `id` for the internal value the next tool call needs.
- Use `label` for what the user sees.
- For ordinary single-select and multi-select cards (`variant: "default"`), keep
  options label-only. Do not add per-option `description` unless the user cannot
  distinguish the choices from labels alone.
- Use `description` mainly for voice cards. Visual style cards should usually
  use only `preview` + `label`.
- When an off-list answer is acceptable, add an explicit option with
  `id: "__other__"` and a `label` in the same language as the rest of the form,
  using the word the user would expect for an off-list answer. The widget will
  turn this option into a text entry when selected. Use `otherPlaceholder` if
  the text entry needs a placeholder.

For visual cards:

- Use real image URLs or data image URLs in `preview`.
- When a live AI-avatar result includes both media types, use its
  `previewVideoUrl` as `previewVideo` and its `previewImageUrl` as `preview`.
  The image is the poster and automatic fallback; never omit it merely because
  a video exists.
- For MG style choices, reuse the active MG skill's shortlist. Use the exact
  Design Style UUID as `id`, its returned name as `label`, and `thumbnailUrl`
  as `preview`.
- For an explicit Design Style catalog picker, map real returned preset metadata
  to `{ id: preset.id, label: preset.name, preview: preset.thumbnailUrl }`.
  `list_presets` is also the MG catalog discovery entry.
- Never hardcode catalog preset ids unless the user already selected one.

For voice cards:

- Use `audioUrl` for the sample file.
- Use the exact `previewUrl` returned by `manage_voice`. Do not pass localhost
  sample URLs or reconstruct an origin; MCP host iframes do not reliably
  resolve editor-local media.
- Keep user-visible descriptions provider-neutral. Describe the voice the same
  way the native ChatCut audition UI does: gender / age range / tone / use case,
  such as `Female / young / friendly, general` or `男 / 中年 / 低沉知识解说`.
  Do not show provider names like ElevenLabs or Doubao in option descriptions.
- Keep each option's type and selection fields together:
  - Official voice: use the returned `voiceId` as the option `id`, retain its
    `provider`, and submit the selected tuple through `submit_voice`.
  - Custom voice: use the returned `customVoiceId` as the option `id`, preserve
    its exact `previewUrl`, and call `manage_voice` with `voiceType:"custom"`,
    `action:"apply"`, and that `customVoiceId` after selection. Do not require a
    custom tuple to contain an official `voiceId` or `provider`.

### Current Gaps

`ask_followup_questions` is for structured answers only. It does not support native
custom HTML, timeline parameter bridges, editor item selection, or file upload
fields. For files already held by the agent runtime or attached directly to the
chat outside this card, pass the readable local path to Desktop's `push_asset`
tool. Do not upload the file through an external media-import session.

### Example

```json
{
  "title": "Your video idea",
  "prompt": "Choose or fill in what you have in mind so ChatCut can pick a good starting direction.",
  "submitLabel": "Send idea",
  "messagePrefix": "Continue with this video direction:",
  "fields": [
    {
      "id": "goal",
      "label": "What's the main goal of this video?",
      "type": "single",
      "required": true,
      "options": [
        { "id": "product_intro", "label": "Product intro" },
        { "id": "social_ad", "label": "Social ad" },
        { "id": "__other__", "label": "Something else" }
      ]
    },
    {
      "id": "elements",
      "label": "What should it include? (Select all that apply)",
      "type": "multi",
      "required": true,
      "options": [
        { "id": "broll", "label": "B-roll" },
        { "id": "logo", "label": "Brand logo" },
        { "id": "__other__", "label": "Something else" }
      ]
    }
  ]
}
```

## MG Design Style choices

The MG skill owns discovery and applying the answer. Reuse its shortlist from
`manage_design_style list_presets`; render catalog cards with their exact UUIDs:

```html
<widget>
  <form-visual
    id="mg_style"
    label="Choose a Motion Graphics style"
    required="true"
  >
    <visual-option preset-id="CATALOG_DESIGN_STYLE_UUID" />
  </form-visual>
</widget>
```

For a saved custom style, use an ordinary `visual-option` with its Design Style
UUID as `value`, returned name and `thumbnailUrl` as `media`. Keep the
label-to-UUID map and whether the choice is a saved style or catalog preset.
Previewing a style requires no media import. An Other answer returns to discovery,
not style application. Keep the existing create/clone actions for avatar/voice
pickers; write only real choices and use the form's automatic Other branch.
