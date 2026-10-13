# Asset Gathering Reference

Load this reference as needed. Do not execute every step in order by default. Decide which assets are needed from the current task goal, and gather only the necessary assets.

**Efficiency principle**: minimize tool calls. Use one Firecrawl call to get all information, download assets in parallel, and register assets in batch.

---

## URL gathering with Firecrawl

**Tool**: `web_browser` (ChatCut backend proxy)

Extract branding information and image lists in one call. Do not split this into multiple calls:

```ts
web_browser({
  url: "<url>",
  formats: ["branding", "images"],
  query:
    "Extract: product name, slogan, core features (each with title and one-line description), CTA text, target audience",
});
```

Returned data:

| Field                   | Content                                             | Typical use                          |
| ----------------------- | --------------------------------------------------- | ------------------------------------ |
| `branding.colors`       | Brand colors: primary, secondary, accent hex values | MG colors / Seedance style words     |
| `branding.uiComponents` | Gradients / button styles                           | MG background / button recreation    |
| `branding.typography`   | Fonts                                               | MG text                              |
| `branding.spacing`      | Border radius / spacing                             | MG card style                        |
| `branding.logo`         | Logo URL or data URI                                | Opening/ending; never redraw with AI |
| `images`                | Image URL list                                      | Visual assets                        |
| `data.json`             | Product name / slogan / selling points / CTA        | Copy planning                        |

### Fallback

If Firecrawl returns empty data, times out, or hits 403, retry with `waitFor: 5000, timeout: 60000` or `country: "US"`. If it still fails, use `actions` to scroll/load content or `execJs` to extract data.

---

## Brand -> Design Style

Whatever the source (scraped page or user-provided materials), the brand becomes this project's Design Style before any generation starts. Save it once with `manage_design_style` `action: "create"`; it auto-applies, and later MG submits pick it up through `designStyle: "core"`.

| Brand source                       | designSpec field                                                                                                                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `branding.colors`                  | `colors[]` - `role` says what the color is for (`primary`, `background`, `CTA button`), `value` is the hex                                                                           |
| `branding.typography.fontFamilies` | `fonts[]` - `role` `heading` / `body`, `family` is the CSS family                                                                                                                    |
| extracted or user-provided logo    | `logos[]` - the resolved logo URL, `role` `primary` / `wordmark` / `icon`                                                                                                            |
| product tone in one line           | `styleGuide` - one plain string, abstract tone only ("Modern, technical, confident."). Not an object, and never layouts, radii, fonts, or colors already carried by the fields above |

Border radius, spacing, and button styles have no designSpec field. Keep them for the MG brief's brand notes; do not stuff them into `styleGuide`.

Save what was actually extracted. Do not invent a color or a font to fill a role, and do not fold catalog-preset aesthetics into the brand.

**When the brand cannot be obtained** - no URL, extraction failed, and the user has no materials - say so, then fall back to the normal style alignment in the active MG skill (`create-motion-graphics` when available for direct authoring, otherwise `motion-graphic-gen`; catalog presets). Do not silently substitute a preset for a brand the user expected you to use.

---

## Logo extraction

`branding.logo` can appear in three forms:

**HTTP URL** -> download directly with curl.

**data URI** (`data:image/svg+xml;utf8,...` or `data:image/svg+xml;base64,...`):

- A data URI is not a network address. It embeds file content directly inside a string.
- **Never** paste the full data URI into chat text, `Write` tool arguments, command-line arguments, or inline `node -e` scripts.
- If the current context already shows the `branding.logo` value, **do not copy it**. Fetch branding again, write the JSON to disk, then process it with the script.
- The only recommended flow:

First fetch branding, then write the full result to the workspace and extract with the script:

```ts
web_browser({ url: "<url>", formats: ["branding"] });
// Write the full returned JSON to ai-working/promo/branding.json with the Write tool.
```

```bash
node .claude/skills/app-promo-guide/scripts/extract-asset-from-json.mjs \
  ai-working/promo/branding.json \
  ai-working/promo/assets \
  logo \
  data.branding.images.logo \
  data.branding.logo \
  branding.images.logo \
  branding.logo
```

`extract-asset-from-json.mjs` tries these field paths in order. After finding the first string value, it processes it. If the value is a data URI, it first writes `<basename>.datauri`, then decodes it into a real file.

**Empty value** -> filter the `images` list for URLs containing "logo"; if still missing, ask the user to provide the logo.

**The logo must be registered as an asset and used in the video, such as opening or ending. Never simulate it by drawing text in MG code; that is AI redrawing.**

---

## Image / video download

Choose images with the video concept in mind: which image can be used in which part of the video? Product UI screenshots, feature demo images, and template preview images can all be useful; thumbnails, duplicates, and purely decorative backgrounds are usually unnecessary. Download only what you plan to use.

**Parallel download**: webp, png, jpg, mp4, and webm can all be used directly and do not need format conversion. Use absolute paths plus `-o` filenames to avoid path ambiguity:

```bash
mkdir -p $WORKSPACE_DIR/ai-working/promo/assets && \
curl -sLo $WORKSPACE_DIR/ai-working/promo/assets/screenshot1.webp "<url1>" & \
curl -sLo $WORKSPACE_DIR/ai-working/promo/assets/screenshot2.webp "<url2>" & \
curl -sLo $WORKSPACE_DIR/ai-working/promo/assets/hero.png "<url3>" & \
wait
```

---

## Batch-register into the asset library

After download, use `push_asset` to register assets in batch. Do not register one by one:

```
push_asset(filePath: [
  "ai-working/promo/assets/logo.svg",
  "ai-working/promo/assets/screenshot1.webp",
  "ai-working/promo/assets/screenshot2.webp",
  "ai-working/promo/assets/demo.mp4"
])
```

Batch mode automatically uses filenames as asset names and uploads/registers in parallel. Type is detected automatically from the file extension.
