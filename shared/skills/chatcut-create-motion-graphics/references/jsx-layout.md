# JSX layout

Read this before implementing text or connected shapes/symbols in an MG.

## Text layout

For text-bearing MGs, design the settled frame as a real layout before animating. Use flexbox or grid, `gap`, `padding`, `maxWidth`, `lineHeight`, and natural wrapping for related text blocks. Do not stack readable text with independent hardcoded `top` values unless the text is intentionally decorative or typographic art.

Editable text may become longer than the default. Reserve space for plausible longer copy, allow wrapping with `whiteSpace: "normal"` and `overflowWrap: "break-word"`, and reduce hierarchy, size, density, or change form when the content cannot fit cleanly.

Animated transforms do not affect layout. If text scales, pulses, slides, or staggers near other text, leave visual headroom for the largest animated state. Intentional overlap may be used for graphic layers, shadows, marks, or decorative typography; ordinary readable text must not collide.

Avoid forced `<br>` or manual line breaks for dynamic text unless each line is deliberately fixed. Prefer width-constrained wrapping.

For a Remotion entry, an exported component can use this shape. HTML entries
follow the lifecycle in [Runtime APIs](runtime-api.md) instead.

```javascript
import { useCurrentFrame, useVideoConfig } from "remotion";

export default function Component({ item }) {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const props = item.props || {};
  const accentColor = props.accentColor;

  const rootStyle = {
    position: "absolute",
    inset: 0,
    backgroundColor: "transparent",
  };

  return <div style={rootStyle}>{/* content */}</div>;
}
```

## Connected shapes

A character, illustration, or compound shape is one visual entity. A shared SVG
coordinate space and named anchors can keep connected parts aligned. Other
structures are valid when their parts stay aligned throughout the animation.

## Export-safe symbols

Never use Unicode arrows, triangles, emoji, dingbats, or icon-font glyphs as required visual elements (for example `→`, `➔`, `➜`, `▶`, or `➤`). Font availability can differ between preview and the target export renderer. Draw arrows and other symbols with CSS geometry or an inline SVG path/polygon. Keep an arrow shaft and tip in one SVG and one coordinate system. If using `<marker>`, define it in that SVG, give it a unique ID, and verify every `marker-start`/`marker-end` reference resolves. Do not rely on external SVG files, stylesheets, or fonts for critical visual content.

## Renderer fonts

Motion Graphics must use fonts available to ChatCut's renderer so preview and export stay consistent. Do not rely on machine-specific system fonts such as `STKaiti`, `PingFang SC`, `Microsoft YaHei`, `Arial`, `Helvetica`, `Comic Sans MS`, `system-ui`, `-apple-system`, or generic CSS families as the primary rendered font; availability differs between machines and may cause fallback.

When choosing or replacing a font, call `search_fonts` and use the returned canonical family name verbatim as the `fontFamily` value and matching `font` property `defaultValue`. Use Google Fonts or project custom fonts returned by the catalog. If a requested machine-specific font is not in the catalog, explain that consistent rendering cannot be guaranteed, search for a supported alternative with a similar feel, and use it unless the user explicitly accepts font fallback.
