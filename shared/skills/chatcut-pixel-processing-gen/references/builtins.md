# Built-in pixel processing

### `builtin:effect-zoom` uses the same track-bound placement as every effect

Effects always have timeline geometry. For a whole-clip effect, pass `targetItemId`; ChatCut resolves it to a clip-anchored range covering that clip. For an explicit timeline range, pass `trackId` + `startFrame` + `durationFrames`.

```text
# Zoom on the entire video clip
edit_item({adds:[{type:"pixel-effect",assetId:"builtin:effect-zoom",targetItemId:"<clip-id>",propertyOverrides:{magnification:1.5,shape:"hold"}}]})

# Zoom on a sub-range of the clip (e.g. frames 90–150 only, a punch zoom on a beat)
edit_item({adds:[{type:"pixel-effect",assetId:"builtin:effect-zoom",trackId:"<trackId>",startFrame:90,durationFrames:60,propertyOverrides:{magnification:2,shape:"punch"}}]})
```

Use `preview_timeline({views:["timeline"],tracks:["V1"]})` to obtain track item ids and timeline-frame ranges. Use `inspect_item({itemId:"..."})` when exact item detail is needed.

| Key             | Type   | Range / values                             | Default | Notes                                        |
| --------------- | ------ | ------------------------------------------ | ------- | -------------------------------------------- |
| `magnification` | number | 1–4                                        | `1.5`   | Zoom factor; 1 = no zoom, 2 = 2× in          |
| `focalPointX`   | number | 0–1                                        | `0.5`   | Horizontal focal point (0 = left, 1 = right) |
| `focalPointY`   | number | 0–1                                        | `0.5`   | Vertical focal point (0 = top, 1 = bottom)   |
| `shape`         | select | `punch` / `hold` / `slow-push` / `instant` | `hold`  | Animation curve                              |
| `easeInFrames`  | number | 0–60                                       | `8`     | Frames to ramp in                            |
| `easeOutFrames` | number | 0–60                                       | `8`     | Frames to ramp out                           |

Omit `propertyOverrides` entirely for default zoom. Send only the keys you want to change — patch semantics.

Zoom uses the supplied focal point. Face-tracking zoom, AI super resolution,
and video stabilization are not available in this Desktop release.

### AI Portrait Cutout is a built-in Desktop effect

For portrait cutout, background removal, transparent portrait background, 人像抠图, 抠图, or 去背景, use the built-in effect. Use this existing effect rather than implementing segmentation in HTML.

```text
browse_library(category: "effects", query: "抠图")
edit_item(adds: [{
  type: "pixel-effect",
  assetId: "builtin:effect-ai-portrait-matte",
  targetItemId: "<video-item-id>"
}])
```

This effect is supported by ChatCut Desktop on macOS, Windows, and Linux. It must target one complete `video` or `image` clip: pass `targetItemId` only, without `trackId`, range fields, or a GIF target. Desktop downloads the model and prepares the matte cache automatically; processing may remain visible briefly after the timeline edit succeeds.

Optional `propertyOverrides`:

| Key                 | Type   | Range / values              | Default   |
| ------------------- | ------ | --------------------------- | --------- |
| `edgeFeather`       | number | 0–100                       | `0`       |
| `matteOffset`       | number | -50–50                      | `0`       |
| `outlineStyle`      | select | `none` / `solid` / `dashed` | `none`    |
| `outlineColor`      | color  | CSS color                   | `#ffffff` |
| `outlineWidth`      | number | 1–20                        | `10`      |
| `outlinePlacement`  | number | -50–50                      | `7`       |
| `outlineDashLength` | number | 1–100                       | `12`      |
| `outlineDashGap`    | number | 0–100                       | `8`       |
| `outlineDashOffset` | number | -100–100                    | `0`       |

### Linear Mask

For a linear or feathered gradient mask, use the built-in effect:

```text
browse_library(category: "effects", query: "线性蒙版")
edit_item({adds:[{type:"pixel-effect",assetId:"builtin:effect-linear-mask",targetItemId:"<clip-id>",propertyOverrides:{direction:180,stops:[{position:0,opacity:1},{position:0.25,opacity:1},{position:1,opacity:0}]}}]})
```

`direction` is 0–360 degrees; 180 fades from top to bottom. `stops` is an
array of 2–8 `{position, opacity}` objects, with both values in 0–1. Always
send the complete stops array when changing the gradient. Update the placed
effect with `edit_item updates:[{type:"pixel-effect",id:"<effect-id>",propertyOverrides:{stops:[...]}}]`;
omitted properties such as direction are preserved.

### Inline vs block

Effect items have two placements, both with a concrete time range:

- **Inline**: pass `targetItemId`; the effect covers the whole item and follows it when it moves or resizes.
- **Block effect**: pass `trackId` + `startFrame` + `durationFrames` for an absolute timeline range.

Use `targetItemId` for whole-clip effects. Use explicit track geometry only when the requested range differs from a clip's full duration.

### Built-in LUT properties

```text
edit_item({adds:[{type:"pixel-effect",targetItemId:"<clip-id>",assetId:"builtin:slog3-s709",propertyOverrides:{intensity:1}}]})
```

| Key         | Type   | Range | Default | Notes                          |
| ----------- | ------ | ----- | ------- | ------------------------------ |
| `intensity` | number | 0–1   | `1`     | LUT strength; 1 = full applied |

To swap: delete the effect and re-add with a different `assetId`. To remove: delete the effect item.

User-uploaded `.cube` LUT assets take this exact same shape — only `assetId` differs. See "Applying an Existing LUT Asset" below.
