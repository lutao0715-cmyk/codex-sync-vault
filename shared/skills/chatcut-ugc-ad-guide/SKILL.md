---
name: ugc-ad-guide
description: |
  Guide for making UGC-style product ad videos for PHYSICAL e-commerce products (Amazon / Shopify / TikTok Shop / 实体产品 / 带货 / 卖货). Auto-extracts product info from a URL or user-provided images, writes a high-converting UGC prompt, then generates via AI video. Use when the user wants a product ad / 产品广告 / 带货视频 / 卖货视频 / 电商广告 for a physical product. NOT for software / SaaS / app / website promos; those go through app-promo-guide instead.
user-invocable: true
---

# UGC Ad Guide

End-to-end guide for producing UGC-style product ad videos: scriptwriting + AI video generation.

## What this skill covers

15-second 9:16 vertical UGC-style product ad videos, generated end-to-end via Seedance 2.0 with `omni_reference` mode. The skill's value-add is the scriptwriting expertise (writing rules + 11 product-category references + creative toolbox).

Multiple narrative variants are supported (standard 5-part / ASMR unboxing / before-after / 4-part). The agent picks based on product category and selling points. See Phase 2.

## Required inputs

Three entry points based on what the user provides:

| Entry                  | User provides                                                       | Flow                                                |
| ---------------------- | ------------------------------------------------------------------- | --------------------------------------------------- |
| **A. URL**             | Product page link (Amazon / Shopify / etc)                          | Phase 1 extract → Phase 2 script → Phase 3 generate |
| **B. Images + Info**   | Product images (3-4 multi-angle) + name / category / selling points | Phase 2 script → Phase 3 generate                   |
| **C. Images + Prompt** | Product images + a written prompt (power-user shortcut)             | Phase 3 generate directly                           |

For all entries: 3-4 multi-angle product images are the minimum visual input. Without them, generation can't proceed. See Phase 1 "Image Rules" for selection criteria.

**When the user starts without specifying an entry, ask via `<choices/>` first.** "URL or upload?" is a single branching decision, the canonical choices case. Don't pile both URL field + file upload + description into one widget upfront. Let the user pick a path, then collect what that path needs:

```text
You can give me the product link, or upload images directly. Which works for you?
<choices options='["Send product URL","Upload product images"]'/>
```

After the user picks, run the Phase 1 extraction (URL path) or move to a focused upload widget (Images path). Entry C (images + prompt) is a power-user shortcut: agent recognizes it from the user's first message rather than offering it as a chip.

## What shapes the ad

This skill applies UGC writing expertise via category references + writing rules. **Most creative decisions are made by the agent**; user mainly confirms the final script. Three categories of decisions:

| Agent decides (using references)               | User aligns upfront (with defaults)                                                   | User confirms (gate)                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Narrative variant, by Category Quick-Reference | Target length (default 15s, max 15s)                                                  | Final script (User Script version) before Phase 3 generation |
| Subject type (face / hands / pet)              | Target platform & aspect (default 9:16 vertical for TikTok/Reels/Shorts)              |                                                              |
| Hook type, by product positioning              | Selling-point priority (which to highlight if multiple; agent picks if not specified) |                                                              |
| Sound mode, by Category BGM matrix             | Override preferences if any ("use male VO" / "no BGM" / "Spanish VO")                 |                                                              |
| Wow Moment, from main selling point            |                                                                                       |                                                              |

Most user-aligned dims have sensible defaults. Only ask when key info is missing or conflicts with defaults; don't run a checklist of all 4 every time.

## Flow

4 phases. Phase 1 only applies to URL entry. **You must confirm with the user at each key checkpoint before continuing** (unless the user has explicitly asked to run end-to-end without stopping). Checkpoints:

- **Product info and assets** (end of Phase 1): extracted info accurate? selected images right?
- **Creative direction** (within Phase 2, before detailed script writing): narrative / persona / sound mode aligned?
- **Full script** (end of Phase 2, before generation): ready to generate?
- **Generation result** (end of Phase 3): output OK or iterate?

**Don't bundle multiple checkpoints into one response.** Show one checkpoint, wait for user response, then the next; don't show extracted info + creative direction + script all at once asking for one combined approval.

Upstream errors compound: wrong extracted info → wrong script → wasted generation credits.

> **Phase 2 (scriptwriting) is the core**: script quality directly determines video quality.

---

## Phase 1: Extract Product Info (entry A only: URL)

> User already provided images + info → skip to Phase 2.
> User already provided images + prompt → skip to Phase 3.

### Extraction Mindset

**Extract with "what video am I going to shoot" in mind**; don't just mechanically scrape data:

- What user group and use case is this product for? What are the main selling points?
- Which product images work best as generation references?
- Which selling point makes the best **Wow Moment**?
- Any ready-made hooks from user reviews? ("Game changer", "Total lifesaver")
- Any discount/promo for the CTA?

### What to Extract

| Priority         | Content                                                                       | Notes                                                                                                 |
| ---------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **P0 Must**      | Product images (4 to 5 selected), product name, category, core selling points | Can't write a script without these                                                                    |
| **P1 Important** | Price/discount, dimensions/weight/specs, target audience                      | Makes the script more precise: exact dimensions in the prompt work far better than vague descriptions |
| **P2 Bonus**     | Rating/review count, user photos, ranking, promo/coupon                       | Use for Proof and CTA if available                                                                    |

> Even with incomplete info you can write a script: fill gaps with category common sense.

### Image Rules

**Principle**: URL to Ad defaults to **Seedance 2.0 omni_reference mode**. Product images are required; if none available, ask the user to provide them.

**Why multiple angles**: these product images are sent together as Seedance 2.0 `referenceImages` in omni_reference mode. Front-only → the model only knows the front → it will hallucinate the sides/back. Multi-angle images give the model a complete mental model of the product's appearance, so it stays accurate when the product rotates, tilts, or is picked up in the video.

**Selection target**: 3 to 4 product images from different angles, covering the product's main visible surfaces.

| Priority | Type                         | Purpose                                           | Count                         |
| -------- | ---------------------------- | ------------------------------------------------- | ----------------------------- |
| **1**    | 45° angled side view         | Shows front + side simultaneously (most info)     | 1 (preferred as frontalImage) |
| **2**    | Front / back / other side    | Covers angles the main image missed               | 1 to 2                        |
| **3**    | Dimension diagram / close-up | Helps model understand scale and material         | 0 to 1                        |
| **4**    | Lifestyle/scene image        | Low reference value: only use if < 3 images above | 0 to 1                        |

**Don't select**: text-only infographics, multi-product group shots (confuses subject identification), heavily retouched marketing images (differs from actual product).

**Safety check**: verify images during extraction. Catch issues early to avoid wasted work downstream:

- **IP/Copyright**: video models reject any recognizable IP content. If the product involves any of these, tell the user it can't be generated: Disney/Pixar, Marvel, DC, Nintendo (Mario/Pikachu), anime characters (Dragon Ball/Naruto/One Piece etc.), real celebrity/public figure likenesses, well-known game IPs. If one character is blocked, all characters from the same franchise are also blocked. Note: ordinary (non-celebrity) human faces in product images are fine; only recognizable IP / public-figure faces are blocked.
- **Prohibited content**: nudity, graphic violence, negative portrayal of major brands (also rejected).
- **Brand logos**: avoid images where a brand logo is too prominent (triggers moderation rejection).

**Dimensions → prompt**: extracted dimensions must go into the prompt. Specific values produce far better results than vague descriptions ("40oz stainless steel tumbler, 10.5 inches tall" > "a large tumbler").

**Asset registration**: register all downloaded product images to the asset library for Phase 3 reference.

### Extraction Flow

**Tool**: `web_browser` (ChatCut backend proxy)

**Amazon**: extract the ASIN from the URL (`/dp/XXXXXXXXXX`), construct `https://www.amazon.com/dp/<ASIN>` (prefer .com).
**Other sites**: use the original URL directly.

#### Single call to extract everything

**Amazon** (structured data + hiRes images, single API call):

```ts
web_browser({
  url: "https://www.amazon.com/dp/<ASIN>",
  query:
    "Extract: product title, brand, price, original price, discount percentage, rating, review count, all selling points (bullet list), product dimensions, weight, material, capacity, key specs, top 3 customer review excerpts, any active coupon",
  execJs:
    'JSON.stringify([...new Set((document.body.innerHTML.match(/"hiRes"\\s*:\\s*"(https:\\/\\/m\\.media-amazon\\.com\\/images\\/I\\/[^"]+)"/g)||[]).map(m=>m.replace(/"hiRes"\\s*:\\s*"/,\'\').replace(/"$/,\'\')))])',
  waitFor: 3000,
  country: "US",
});
```

Returns: `data.json` (product info) + `data.actions.javascriptReturns[0].value` (hiRes image URL array).

**Generic e-commerce (Shopify / independent stores)**:

```ts
web_browser({
  url: "<url>",
  query:
    "Extract: product name, brand, price, currency, description, key features (bullet list), material, dimensions, weight, colors available, rating, review count, all product image URLs",
});
```

#### Verify + Fallback

Product name empty or images empty → extraction failed. Try each fallback once, in order:

1. **Firecrawl retry** (add `waitFor: 5000, timeout: 60000`, or switch to `country: "US"`)
2. **Firecrawl with actions** (use `actions` to scroll/wait for lazy content, or `execJs` to extract from JS)
3. **WebFetch / WebSearch / ask user to provide**

#### Download Images

Select images from extraction results, view them in parallel to verify (faces / IP / angles), then register to the asset library in batch (do not register one by one). **Registration is a hard prerequisite for the confirm step below: the user can only see what's in the asset library; a textual description like "img1: clean front shot" is not a substitute for the image itself.**

```bash
mkdir -p ai-working/images && cd ai-working/images && \
curl -sLO "<img1_url>" && \
curl -sLO "<img2_url>" && \
curl -sLO "<img3_url>"
```

✋ **Confirm product info and assets with the user** before moving to script writing (assets must already be registered to the library so the user can see thumbnails; don't ask to confirm by filename or description):

- Product info (name / category / target audience / selling points): accurate? anything to correct or add?
- Selected images (3-4 multi-angle): right ones to use? any face/IP/logo issues to swap?

---

## Phase 2: Write the Script (= Prompt)

> **This is the core of the entire workflow.** Script quality directly determines video quality.

### Pre-script alignment

Before composing the detailed script, summarize the creative direction and wait for user buy-in:

- **Narrative variant** (e.g., "Before/After audio comparison")
- **Subject & persona** (e.g., "Female 20-30s, hands+product close-up")
- **Sound mode** (e.g., "No BGM, audio quality is the demo")
- **Wow Moment** focus
- **User-aligned dims**: target platform / length / selling-point priority

✋ **Confirm creative direction with the user**; wait for buy-in before composing the detailed script. If user wants different direction, adjust before writing.

### Load References

Before writing, load the reference file for the product's category. References contain complete prompt examples + pattern breakdowns + BGM/SFX guidance.

**Category → reference file mapping**:

| Category                          | Reference file                | Example products                                                        |
| --------------------------------- | ----------------------------- | ----------------------------------------------------------------------- |
| Electronics / audio / peripherals | `references/electronics.md`   | Speakers, mice, headphones, cables, mics, routers                       |
| Kitchen                           | `references/kitchen.md`       | Ice makers, cutting boards                                              |
| Home / appliances                 | `references/home.md`          | Egg holders, projectors, TVs, lamps, mini-fridges, tumblers, rugs, mops |
| Beauty / personal care            | `references/beauty.md`        | Mascara, face masks, soap, hand warmers                                 |
| Fashion / wearables               | `references/fashion.md`       | Shirts, compression socks                                               |
| Automotive                        | `references/automotive.md`    | Steering wheel covers, motor oil                                        |
| Outdoor / sports                  | `references/outdoor.md`       | Solar panels, ski goggles, luggage, exercise bikes                      |
| Crafts / tools                    | `references/crafts-tools.md`  | Paint pens, crochet kits, craft knives, chainsaws                       |
| Food / beverage                   | `references/food-beverage.md` | Instant noodles, energy drinks                                          |
| Pets / toys                       | `references/pets-kids.md`     | Bird food, dog bones, building blocks                                   |
| Cleaning / household              | `references/cleaning.md`      | Cleaning sprays, insecticides, gloves                                   |

**Loading flow**:

1. Identify the product category → read the corresponding reference file
2. If category is ambiguous, load 2 to 3 related files (e.g. "portable mini-fridge" → `home.md` + `electronics.md`)
3. **After reading, you must pick a narrative framework from a same-category example as your starting point**, then adapt for the current product. Don't skip the references and write from scratch; the reference patterns are battle-tested and produce better results than improvising
4. Each reference example's Breakdown section explains key decisions (hook type, Wow Moment, sound strategy); apply these directly to the current product

### Build the Script Around Selling Points

**The script must be based on the real selling points extracted in Phase 1; never invent features.** Weave specific features, data, and user pain points from the selling-point list into the visuals and voiceover. A 15s video can only cover 1 to 2 selling points deeply: pick the one with the most visual impact for the Wow Moment, mention the rest quickly via VO.

### Style Goal: Native Short-Form Ad

**The goal is to generate something that looks like a real person filmed it on their phone for TikTok / Shorts / Reels, not a polished brand film.**

- **Camera angle**: phone POV, handheld, phone propped on desk/table
- **Setting**: real living spaces (kitchen counter, desk, living room, car interior), not a studio
- **Lighting**: natural light or everyday sources (window light, ring light, room light)
- **Style prefix**: start the prompt with `Authentic phone-shot UGC style.` + scene/lighting description (format/duration/aspect ratio are controlled by parameters, not written in the prompt)

### Subject & Persona

**Core principle: imagine a real person filming this product. How would they naturally appear on camera?**

- Product used on face/body (skincare, wearables, food) → naturally show face/body; not showing it looks fake
- Product operated by hands (electronics, kitchen tools, home goods) → product + hands, simple and effective
- The decision is based on how the product is used, not a fixed rule

**VO and persona should match the product's target audience.** Makeup remover → female voice. Power tools → male voice. Universal categories → either. The viewer decides within the first second whether "this is for me." When unsure, look at the reviews: whoever is buying is whose voice and image you should use.

**Keep characters consistent**: define appearance once (~30 characters), copy to all subsequent shots.

**Character definition best practices**, be this specific:

- `American male, 20-30s, casual hoodie, energetic and excited` (ice makers, electronics)
- `American female, 20-30s, matching activewear in muted tones` (fitness equipment)
- `American mom, warm voice, cozy oversized sweater` (crafts, kids)
- `Male, 30-40s, handy/DIY type, confident with humor` (tools, automotive)
- Age + clothing + tone: all three are required. The character must match the target buyer demographic

### Voiceover = Off-Camera Narration

VO is independent narration, **not the on-screen person talking to camera** (current video models still can't reliably lip-sync). On-screen characters only perform actions and expressions.

**VO language must sound native**: use TikTok/short-form speech patterns, not ad copy. "Dead by noon" > "runs out quickly", "ate that stain alive" > "removed the stain effectively", "the good ice" > "high-quality ice".

### Sound Design

Seedance 2.0 with `audio: "on"` generates voice and ambient sound. When writing the prompt, imagine what the viewer will hear:

- **Satisfying sounds** (boost completion rate): ice crashing / lid click / snap / pour / scrape / squeak
- Embed sound cues in scene descriptions: `pours ice, cubes crash into tumbler`, `screw-on lid tightens with a squeak`
- ASMR texture works well for electronics / unboxing / material-focused products

**Describe SFX per segment**, not just "embed sound cues." Each time segment should state what the viewer will hear:

- Vague: `(3-7s) Show the ice maker working.`
- Specific: `(3-7s) Pull open the ice drawer. Close-up: ice nuggets dropping rapidly, plop-plop-plop rhythm. SFX: rapid-fire ice dropping sounds.`

**BGM style by category**: see Category Quick-Reference table below for per-category BGM constraints (the BGM column).

**Rhythm pattern**: most high-converting ads use "quiet start, loud drop":

- First N seconds pure ASMR / ambient (no BGM) → BGM drops in at the Wow Moment
- Example: ice maker, 7s of ice ASMR → music explodes when coffee is poured over ice
- Example: charging cable, old cable gets "cricket sounds" → new cable enters with Phonk blast
- The volume contrast itself creates an emotional arc

### Script Structure

**5-part structure** (most common):

| Part    | Core task                           | Duration         |
| ------- | ----------------------------------- | ---------------- |
| Hook    | Stop the thumb, prevent scroll-away | 2 to 4s          |
| Problem | Trigger empathy (**brief**)         | 1 to 2s          |
| Demo    | Show product + Wow Moment           | **largest part** |
| Proof   | One trust signal                    | 2 to 3s          |
| CTA     | Drive action: close, don't expand   | 2 to 3s          |

**Part count and duration are flexible.** References include 4-part, 5-part, and non-standard structures. Decide based on the product; don't force 5 parts. Demo is the flex segment: if Problem only needs 1s, Demo gets 8s.

**Variants** (choose based on product):

- **4-part** (Hook → Demo → Proof → CTA): product has built-in conflict (e.g. stress test)
- **ASMR unboxing** (no voice): visually premium electronics
- **Before/after contrast** (old vs new): upgrade/replacement products

### Writing Rules

1. **Tone like a friend recommending**: "This thing is insane" > "This product features..."
2. **VO ≤ 60 words** (15s video): one continuous monologue, read in one breath
3. **Hook = emotional hook + physical action**. Pick the emotion first (fear / identity / shock / urgency / disgust), then pair with an opening action (slam / drop / flip / rip / pour / toss). The action is the vehicle; the emotion is the goal.
   - Weak: `Hand slams product on table` (action only, no emotion)
   - Strong: `"Stop spraying, you're fighting a losing battle." Hand slaps bait station onto counter` (emotion first, then action)
   - Strong: `Oil glugs into a deep pot, excessive, almost overflowing. Hand shoves oil aside and SLAMS the air fryer onto the counter` (visual creates disgust, action introduces solution)
4. **Every Demo has one Wow Moment**: a single visual "wow" instant
5. **One scene = one shot + one core action.** Don't pack 4 to 5 actions into one sentence
6. **Problem ≤ 2s**: brief, just enough
7. **CTA closes, doesn't open**: no new information
8. **Single environment.** Don't switch settings in 15s. For portability selling points, mention it in VO + demo in the same setting

**Actions and scenes should be written to "filmable" specificity**; compare:

| Vague (AI can't execute)          | Specific (AI can produce)                                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `Show the product features`       | `Fingers firmly press the self-cleaning button. Camera cuts to ice cubes rattling down into the tray, rapid-fire pebble ice tumbling out.` |
| `Display the product in use`      | `Single-hand grip on the chainsaw. Rev it up. Attack a 6-inch log, instant cut through, sawdust flying, clean cross-section.`              |
| `Person uses the product happily` | `Take a big sip of the iced coffee. Deliberately bite an ice nugget, audible crunch. Extremely satisfied expression.`                      |
| `Indoor setting`                  | `Bright kitchen island, natural window light, stainless steel appliances in background.`                                                   |
| `Outdoor`                         | `Mountain trail, golden hour. Backpack on, solar panel clipped to the side pocket.`                                                        |

**Scene definitions should also be specific**: not "indoor" but "bright kitchen island, natural window light." Not "bedroom" but "sitting on bed, natural daylight, like sorting through a fresh delivery." The more specific the scene description, the more accurate the AI-generated visuals.

### Common Mistakes

- ❌ **Thumbs up ending**: too generic and fake. CTA action should relate to the product: bite ice nugget / toss box into cabinet / snap case shut / zip bag closed / lean into camera. Every product has its own closing action.
- ❌ **Using "unboxing showcase" for every product**: check the category quick-reference for the recommended narrative framework. Ant bait should be "tactical deployment," audio products should be "audio quality Before/After"; not every product fits "unbox → show → CTA."
- ❌ **Adding BGM to audio/sound products**: the audio quality comparison IS the entire sound design. Any BGM weakens the core demo.
- ❌ **Vague discomfort visuals in the Problem segment**: either show the wrong method (spray killing ants → fails / deep frying → greasy), or skip Problem and go straight to Demo. "Standing barefoot looking tired" has zero information value.
- ❌ **Repeating the same phrase patterns in VO**: "X can't be wrong," "total game changer" are fine occasionally, but don't use them in every script. The reference examples all use different closing lines.

### Prompt Constraints

- Total prompt **≤ 2500 characters** (API hard limit)
- Style prefix: `Authentic phone-shot UGC style.` (format/duration/aspect ratio are NOT written in the prompt; controlled by parameters)
- Reference images must not have prominent brand logos
- Don't render text into the visuals; text is overlaid in post
- Use specific action verbs: press / scoop / stretch / snap / toss / unfold / pour / yank (not "use" / "try")
- Write the product name + appearance anchors (color/material/dimensions/structure) directly; don't use Kling-specific placeholders

### Creative Toolbox

For Hook Types / Persuasive Phrases / Proof Types / CTA Closing Lines, load `references/creative-toolbox.md` when writing.

The category-by-category decision table stays inline (used every script):

#### Category Quick-Reference

| Category                  | Recommended narrative                          | Recommended hook                         | Wow Moment type                                               | BGM constraint                           |
| ------------------------- | ---------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| Electronics (non-audio)   | ASMR unboxing / stress test / texture close-up | Test                                     | Extreme close-up of materials/build                           | Phonk / Lo-fi                            |
| Audio electronics         | **Before/After audio comparison**              | Pain point (bad audio → good audio)      | Instant audio quality switch (sonic wow)                      | **Mandatory zero BGM**                   |
| Kitchen appliances        | Wrong method vs right / use + result           | Pain point                               | Food/drink final result (crunch/pour/sizzle)                  | No BGM (ASMR is the star)                |
| Home organization         | Before/After comparison                        | Negation                                 | Visual contrast before vs after                               | No BGM or soft ambient                   |
| Cleaning / pest control   | Wrong method → right / tactical deployment     | Pain point                               | Before/after cleaning / time-lapse                            | No BGM or industrial rhythm              |
| Outdoor gear              | Outdoor field test / feature demo              | Identity                                 | Working perfectly in extreme conditions                       | **Mandatory zero BGM** (natural ambient) |
| Accessories / consumables | Compare old item + fast pace                   | Comparison                               | New vs old side-by-side, new crushes old                      | Phonk / heavy bass                       |
| Pet products              | Pet reaction is the focus                      | Pain point / Question                    | Pet's real reaction (excitement/satisfaction/focus)           | Light guitar / zero BGM                  |
| Beauty / personal care    | Application close-up + texture                 | Identity                                 | Texture transformation (thick → absorbed / dry → moisturized) | Upbeat Pop / Light R&B                   |
| Fashion                   | Urgent rec / material physics test             | Urgency ("Stop! Don't buy the wrong...") | Material physics test (stretch-snap)                          | **Zero BGM, voice only**                 |
| Food / beverage           | ASMR eating + visual temptation                | Identity                                 | Food sounds and texture (crunch/pour/sizzle)                  | Lo-fi / warm piano                       |
| Tools / power tools       | Full unboxing → hands-on test                  | Pain point (old tool failing)            | Tool cutting through material (power)                         | **Mandatory zero BGM** (mechanical ASMR) |

### Output: User Script vs Internal Prompt

Generate two versions when writing the script: a **user script** (shown to user) and an **internal prompt** (sent to the video model).

#### User Script (output to user)

Describe the video in user-friendly language. No technical markers (`<<<element_1>>>`, `Authentic phone-shot UGC style.`, etc.).

```text
## Video Script

**Product**: [product name]
**Category**: [category]
**Target audience**: [audience description]
**Visual**: [product+hands / face visible], [why]
**VO**: [female/male voice], [style]
**BGM**: [style / no BGM]
**Duration**: 15s

### Voiceover
"[Complete voiceover, one continuous monologue]"

### Shot List
(0-3s) **Hook**: [visual description + action]
(3-5s) **Problem**: [visual description + action]
(5-11s) **Demo**: [visual description + action]
(11-13s) **Proof**: [visual description + action]
(13-15s) **CTA**: [visual description + action]
```

#### Internal Prompt (not shown, passed directly to Phase 3)

Single complete prompt, ≤ 2500 characters. Assemble in this order:

1. `Authentic phone-shot UGC style.` + scene/lighting (one sentence)
2. `Voiceover: "..."` full narration
3. Describe visuals by time segment using `(0-3s)` `(3-5s)` etc.
4. Write the product name + key appearance anchors (color/material/dimensions/structure) explicitly; don't use `<<<element_1>>>`

**Time segments are flexible**: define them based on content rhythm, no need to force 5 parts. Total must equal video duration.

**Self-check before showing to user**:

1. Does the Hook have a strong opening action?
2. Is the Demo's Wow Moment clear?
3. Do time segments add up to 15s? Total prompt ≤ 2500 characters?

✋ **Confirm the full script with the user.** After self-check passes, show the user script and end the reply with `<choices/>`:

```xml
<choices options='["Looks good, generate","Try a different style"]'/>
```

Wait for explicit choice. Video generation costs credits and is irreversible.

---

## Phase 3: Video Generation

> With the script ready, call the **video-gen skill** to generate. This section covers model selection and parameter guidance; see the video-gen skill for full parameter details.

### Model Selection

Use `seedance2` with three or four registered project image assets as
`refImages`. Read the `video-gen` Seedance reference before submitting.

### How to Call

- `prompt`: the confirmed internal prompt from Phase 2, including timing cues.
- `refImages`: project asset ids for the selected multi-angle product images.
- `durationSeconds`: normally `15` for this workflow.
- `ratio`: normally `"9:16"`.
- `resolution`: `"720p"` unless the user explicitly requests 1080p.
- `name`: a descriptive library name.

Public URLs and local paths are not valid `refImages`. Download each selected
image to a readable local path, register it with Desktop `push_asset`, and use
the returned asset ids.

```ts
submit_video({
  model: "seedance2",
  prompt: "Authentic phone-shot UGC style. 9:16 vertical. ...(full prompt)...",
  refImages: ["<asset-id-1>", "<asset-id-2>", "<asset-id-3>"],
  durationSeconds: 15,
  ratio: "9:16",
  resolution: "720p",
  name: "UGC Ad - [product name]",
});
```

### Execution Rules

1. Submit once after the user confirms the script.
2. Keep the returned `jobId`; use `track_progress` for lifecycle checks.
3. Report a failure with its actionable reason and do not blindly retry.
4. Do not submit the same generation twice in one task.

✋ **Confirm the generated result with the user**: show output, check OK before any post-production.

---

## Phase 4: Post-Production

- **Post-overlay** (not in the prompt): CTA text / product name + price label / BGM
- **VO replacement**: if the native voiceover sounds off, generate TTS separately via the `voice` skill. When replacing against the existing shot list, split the replacement voiceover by voice line or shot segment so each clip can be independently timed and placed. Split at sentence or shot boundaries, keep segments short (≤60 chars when possible), and issue one `submit_voice` call per placed segment.

---

## Tools

| Phase              | Tools                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------- |
| Phase 1 (extract)  | `web-browser` skill (Firecrawl) + image download + `push_asset` (batch register)      |
| Phase 2 (script)   | Reasoning + Phase 2 knowledge + per-category references + `<choices/>` (confirm gate) |
| Phase 3 (generate) | `video-gen` skill (Seedance 2.0 `omni_reference` mode)                                |
| Phase 4 (post)     | Timeline edits + `voice` skill (TTS replacement if needed)                            |

References live in `references/`; see Phase 2's Load References table for the per-category mapping, plus `references/creative-toolbox.md` for hook / persuasive phrases / proof / CTA closing line materials.
