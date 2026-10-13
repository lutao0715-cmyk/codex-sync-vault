# Execution Path: Motion Graphics

A complete workflow for generating a video in Motion Graphics segments.

## Brand Integration

Every MG authored design must include the brand parameters extracted in Phase 1 so the result visually matches the product website:

- **Colors**: primary, accent, background, and text values from `branding.colors`.
- **Fonts**: font family from `branding.typography.fontFamilies`.
- **Corner radius**: borderRadius from `branding.spacing`.
- **Button/CTA styling**: if the MG contains buttons, use styles from `branding.components`.

For delegated MG generation, getting the brand into the finished video requires all three steps:

1. **Phase 1 must have saved the brand as the project Design Style** (`manage_design_style` with `action: "create"`, which applies it automatically). Without this step, the next two have no effect.
2. **Pass `designStyle: "core"` during generation** to include the Design Style colors, fonts, and style guide in the Gemini brief. If the project has no Design Style, this parameter **silently injects empty content** without an error; it cannot replace step 1.
3. **Add only brand constraints that Design Style cannot represent to the brief** (corner radius, button/CTA styling, and logo usage). Do not repeat colors and fonts already in Design Style.

Direct authoring has no `designStyle` submission channel; include these values directly as design constraints and editable properties for `create-motion-graphics`.

Do not leave brand information only in chat text, or replace an existing brand with a catalog preset for a branded promo.

## MG Authoring Requirements

**Skill**: load `create-motion-graphics` when available for direct authoring; otherwise load `motion-graphic-gen` for delegated generation.

- Feature-showcase MGs must use the extracted original images.
- Logo animations must use the extracted real logo.
- With `motion-graphic-gen`, generate editable MGs with `submit_motion_graphic`, following that skill's visual alignment, Design Style reading, and verification workflow. Write a complete generation brief for each segment, retrieve the completed asset with `track_progress`, and add it to the timeline.
- With `create-motion-graphics`, directly author editable HTML or Remotion source files and import the entry with `push_asset filePath`, without calling `submit_motion_graphic`, then add it to the timeline and verify it using the direct-authoring skill.

---

## Mode A: TTS Voiceover Workflow (Default)

**Flow**: generate TTS → match visuals to TTS → background music → timeline assembly.

### A.1 Generate TTS

**Skill**: `voice`

1. Write copy by script section (Hook / Solution / Features / CTA).
2. Generate TTS by section or sentence for easier visual matching.
3. Obtain timestamps for each section and plan the visuals.

**Quality**: polished and professional, moderately paced, with room to breathe. Match languages: Chinese-language product → Chinese voiceover; English-language product → English voiceover.

### A.2 Generate Visuals

Generate an MG for each section according to the storyboard:

- TTS leads the content; visuals follow it.
- Plan each MG duration precisely from TTS timestamps.
- Match meaning: visuals should relate to the current narration.
- TTS need not run throughout; leave room to breathe.

### A.3 Background Music

**Skill**: `music`

Set volume to 0.2–0.3 (voiceover leads; music supports). Match the product's tone, fading in at the start and out at the end.

### A.4 Timeline Assembly

**Tools**：`edit_item` / `edit_track` / `manage_timelines`

Place MG visuals on an available video track. Put voiceover and music on separate audio tracks to avoid overwriting or mixing them on the same track.

- Align MG content changes with the meaning of the TTS.
- Use quick fades between clips (0.1–0.2s).
- Overlay exact text (feature names, CTA, URLs) in post-production.

---

## Mode B: Music-Only Beat-Sync Workflow

**Flow**: generate music → select a section → analyze beats → select key beat points → generate MGs → assemble the timeline.

### B.1 Generate Music and Select a Section

**Skill**: `music`

Choose a section with clear rhythmic variation, strong downbeats, and distinct beat points. Keep the original volume (no voiceover).

### B.2 Analyze Beats

```python
import librosa
y, sr = librosa.load('music.mp3')
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beats, sr=sr)
```

### B.3 Select Key Beat Points

Do not sync every beat. Select the 8–10 most important points: opening (first visual impact), section transitions, climax, and ending (CTA).

### B.4 Author MGs

Implement BPM and key beat times in component timing when authoring MGs so the animation lands on the beat.

### B.5 Timeline Assembly

Use the same track-gravity layout rule above: MG-only visuals collapse to V1, and music-only audio collapses to A1.

Align MG start times precisely with the key beat points.

---

## Reference Examples

### SaaS Productivity Tool · 15s · TTS Voiceover

**Product**: project management tool | Brand colors: dark blue + white

```text
Reference images:
- @Image1: App Logo
- @Image2: Main dashboard screenshot
- @Image3: Kanban view screenshot
- @Image4: Analytics report screenshot

Voiceover: "Still drowning in sticky notes and scattered tasks? Meet ProjectFlow. One clean dashboard for everything. Drag, drop, done. Track your team's progress in real time. Ship faster, stress less. Start free today."

(0-3s) MG: Show text: 'Sticky notes? Scattered tasks?' Brand: #1E3A5F primary, #FFFFFF text.
(3-5s) MG: Show @Image1 logo. Brand: #1E3A5F bg, #FFFFFF text.
(5-9s) MG: Show @Image2 dashboard screenshot. Text: 'One dashboard for everything.'
(9-12s) MG: Show @Image3 kanban screenshot. Text: 'Drag, drop, done.'
(12-15s) MG: Show @Image4 analytics screenshot + logo. Text: 'Start Free', URL 'projectflow.com'.
```

**Pattern**: a text MG pain-point hook, screenshots with text overlays in the middle, and a CTA ending, using consistent brand colors throughout. Expose content and brand fields users may change as properties.

### Creative Design Tool · 15s · Pure Visual Impact

**Product**: AI design tool | Brand colors: purple + gradients

```text
Reference images:
- @Image1: App Logo
- @Image2: User creation 1
- @Image3: User creation 2
- @Image4: Editor interface screenshot

Voiceover: "Design without limits. One prompt, infinite possibilities. From concept to creation in seconds. This is DesignAI."

(0-3s) MG: Show @Image1 logo. Brand: #7C3AED primary, #E9D5FF accent.
(3-6s) MG: Show @Image2. Text: 'One prompt, infinite possibilities.'
(6-9s) MG: Show @Image3. Text: 'From concept to creation.'
(9-12s) MG: Show @Image4 editor screenshot. Text: 'Design without limits.'
(12-15s) MG: Show logo. Text: 'DesignAI', CTA 'Try Free'. Brand: #7C3AED primary.
```

**Pattern**: user creations as source material, minimal voiceover, and a major visual change every 3s, with one authored visual system maintaining consistency.
