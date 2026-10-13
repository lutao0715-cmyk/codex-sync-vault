# Media and MG composition

Use this workflow when an MG includes or is composed with photos, footage or
other production media.

One reference instance may describe a complete composition made from several timeline items. It does not imply one self-contained MG asset. Keep reference screenshots, production materials, and current-project footage distinct.

Default to separate items when the design combines ordinary media with graphics:

- Reusable paper/texture/background: an image or video item behind the composition.
- Current-project photo, product image, or footage: its own media item. The agent selects/replaces, crops, positions, and applies supported effects to it; the user is not expected to assemble the layers manually.
- Typography, shapes, and animated decoration: transparent MG item(s). Split background decoration from foreground text when media must sit between them.

Plan layer order, target media rectangle, start/duration, and entrance timing before authoring. State in the code scope which layers already exist outside the MG, so the reference's photo or paper is not generated again. Apply black-and-white/color/grain to the intended media item rather than accidentally affecting foreground text. Verify effect support on the actual playback/export surface; splitting layers does not by itself prove Web/Desktop parity.

1. Reuse assets from `browse_assets` in the **current project**. Import only production files needed in the output into My Assets. Use `push_asset` for Desktop local files; follow the current tool contract for other sources. Registering project media does not publish it to the public resource library.
2. Place normal production media through `edit_item`, using the returned current-project asset IDs. The agent handles replacing example people, copy, and data with the current task's content. Do not use the reference's complete effect screenshot as a background.
3. Embed media inside an MG only when its visual mechanism needs it, such as image-filled lettering or a tightly synchronized internal mask that available timeline tools cannot express. For this exception, bind `image` / `video` property defaults and overrides to **full current-project asset IDs**, never URLs, local paths, or reference-library IDs. Read via `item.props`, guard empty values, and let the runtime resolve the source. Declaring an image property does not import the file.

Library `hero` / `motion` images are study inputs and need no project import merely to be viewed. Missing production files must be reported or replaced with suitable available materials; never silently omit a required layer.

## Verify media

Inspect the complete timeline composition for crop, effect targets, layer order
and timing. For intentionally embedded media, a correct thumbnail is not enough:
check registration, ID binding and byte readiness when dependencies disappear.
Report missing production layers instead of silently dropping them.
