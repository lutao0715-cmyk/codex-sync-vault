# Desktop Motion Graphic runtime APIs

## Choosing a runtime

The entry determines the runtime: `.html` uses HTML; `.js`, `.jsx`, `.ts` or `.tsx` uses Remotion. Both support editable properties, timeline seeking, native preview and export. Choose for the scene structure and revision needs, not a presumed quality ranking.

- **Remotion:** declarative React composition, reusable components, SVG and frame-derived layouts. Its familiar component model can make text/layout sequences and parameterized diagrams easier to revise.
- **HTML:** direct DOM/SVG/Canvas composition and imperative library lifecycles. Consider it for D3 graphics, p5 drawing, Three.js scenes or GSAP choreography. HTML can also be an excellent choice for typography; Remotion can also draw complex graphics.

### Available library capabilities

Choose a library for the work it simplifies, not as a quality requirement. These modules are registered by Flux's V8 runtimes; no npm install or CDN script is needed. A simple composition may need none of them.

| Creative/implementation need                 | Remotion imports                                                                           | HTML imports                                                                                         |
| -------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Reusable geometric shapes and SVG paths      | `@remotion/shapes`, `@remotion/paths` for geometry, path measurement, drawing and morphing | `d3` for generated geometry; `gsap/DrawSVGPlugin`, `gsap/MorphSVGPlugin` for SVG choreography        |
| Data-driven diagrams and charts              | `d3` for scales, layouts and path data rendered through React/SVG                          | `d3` for DOM/SVG data binding and layouts                                                            |
| Text fitting and responsive composition      | `@remotion/layout-utils`, `@remotion/rounded-text-box`                                     | DOM/SVG layout and measurement                                                                       |
| Coordinated motion                           | `@remotion/animation-utils`, `@remotion/gsap`, `@remotion/motion-blur`                     | `gsap` and its registered SVG plugins                                                                |
| Procedural drawing and variation             | `@remotion/noise`, `p5`, `roughjs`, `paper`                                                | `p5`, `roughjs`, `paper`, `pixi.js`                                                                  |
| 3D geometry, materials, lighting and cameras | No registered Three.js import                                                              | `three`, `three/tsl`, `three/webgpu`, `three-bvh-csg`, `three-mesh-bvh` and selected Three.js addons |
| Existing Lottie animation data               | `@remotion/lottie`, `lottie-web`                                                           | `lottie-web`                                                                                         |
| Mathematical and chemical notation           | Registered MathJax TeX/MathML-to-SVG modules                                               | The same registered MathJax modules                                                                  |

For example, compare data with D3 scales instead of maintaining unrelated bar widths; use path utilities for an evolving contour instead of hand-writing intermediate paths. Choose HTML when an imperative scene or drawing library makes the composition and revisions simpler. D3 and p5 are available in both runtimes, so their use alone does not determine the runtime. Library availability does not imply that every upstream API or renderer backend works in Flux: validate the actual technique.

Only registered bare specifiers resolve. Import D3 from `d3`, not an assumed `d3-*` subpackage; Remotion's `@remotion/gsap` does not imply that raw `gsap` is registered there. HTML's selected Three.js addons include `GLTFLoader`, `SVGLoader`, `FontLoader`, `TextGeometry`; `OrbitControls` is **not** registered. Check a specific addon with native validation rather than assuming the whole upstream addons tree is available.

Keep local helpers beside the entry. The runtime does not install packages during rendering; remote module imports and stylesheets are unavailable. Do not assume Node APIs, external network access or arbitrary npm packages. A missing specifier is an import-availability problem, not evidence that the entire visual technique is unsupported.

Verified HTML import forms include `import * as THREE from "three"`,
`import * as d3 from "d3"`, and `import { gsap } from "gsap"`.
Use the named GSAP export: neither the module namespace nor a default import
is the GSAP animation object in this runtime.

## Additional drawing, animation and notation modules

- **Paper.js (`paper`, both runtimes):** vector paths, curves, path operations and geometric construction. Use an owned PaperScope and canvas when drawing, or feed computed geometry into the composition. Disable independent playback and reconstruct the requested frame.
- **Lottie:** Remotion registers both `@remotion/lottie` and `lottie-web`; HTML registers `lottie-web`. Use available animation data when it fits the brief. For imperative Lottie playback, disable autoplay, seek from the supplied frame/time, wait for setup, and destroy the instance on disposal. A registered import does not guarantee every upstream rendering mode; validate the native result.
- **MathJax (both runtimes):** compose actual mathematical or chemical notation as SVG rather than approximating it with plain text. Registered entry specifiers include `@mathjax/src/js/mathjax.js`, `@mathjax/src/js/input/tex.js`, `@mathjax/src/js/input/mathml.js`, `@mathjax/src/js/output/svg.js`, `@mathjax/src/js/adaptors/liteAdaptor.js`, `@mathjax/src/js/handlers/html/HTMLHandler.js`, and `@mathjax/mathjax-tex-font/js/svg.js`. Registered TeX configuration modules under `@mathjax/src/js/input/tex/` include `ams/AmsConfiguration.js`, `newcommand/NewcommandConfiguration.js`, `configmacros/ConfigMacrosConfiguration.js`, `mathtools/MathtoolsConfiguration.js`, `color/ColorConfiguration.js`, `cancel/CancelConfiguration.js`, `mhchem/MhchemConfiguration.js`, `bbox/BboxConfiguration.js`, `textmacros/TextMacrosConfiguration.js`, and `boldsymbol/BoldsymbolConfiguration.js`. Use these exact registered paths; a bare `mathjax` or arbitrary submodule is not implied.

HTML's registered Three.js addons also cover DRACO and RGBE loading, NURBS curves/surfaces/volumes, convex/parametric/teapot geometry, CCD inverse kinematics, skeleton and buffer-geometry utilities, room lighting and selected stereo/ASCII effects. Use the exact registered addon path and validate the chosen technique. A module such as `three/webgpu` being registered does not establish that a WebGPU renderer is usable on the running native host.

## Typography and font availability

Use CSS `font-family` in HTML and `style.fontFamily` in Remotion. Flux resolves installed system fonts and its Google Fonts / ChatCut hosted-font catalogs. For a catalog family that is not available locally, the host requests and caches the font; do not add a Google Fonts stylesheet, CDN import or `@remotion/google-fonts` dependency. For example, `fontFamily: '"Noto Serif SC", serif'` selects a registered Chinese serif family, while `"Noto Sans SC"` provides a Chinese sans family. These are availability examples, not prescribed design defaults.

Choose a family whose glyph coverage includes the actual copy. A Latin family name such as Georgia does not itself specify the appearance of Chinese characters; those glyphs can come from fallback. Set the intended weight and inspect the rendered letterforms, spacing and wrapping with the real text. Naming a typeface in the brief is not evidence that it rendered.

Playback, export and frame capture wait for pending font requests. A failed request may still render with fallback, and an unknown family is not automatically downloadable. Cached remote fonts persist across restarts. Do not promise a particular face based solely on successful source validation; review the native output. Font choice supports the composition and subject, and does not replace either.

## HTML entry and lifecycle

Use exactly one module script, inline or referencing a local JS/TS file; local stylesheet links and relative module imports stay inside the source directory. The module default-exports `mount({ root, props, timeline, viewport })`, which may be async and returns `render`, `dispose`, and optionally `update`:

```html
<!doctype html>
<html>
  <body>
    <h1 class="title"></h1>
    <script type="module">
      export default function mount({ root, props }) {
        const title = root.querySelector(".title");
        let values = props;
        return {
          update({ props }) {
            values = props;
          },
          render({ timeSeconds }) {
            title.textContent = values.title;
            title.style.color = values.color;
            title.style.opacity = String(Math.min(1, timeSeconds / 0.4));
          },
          dispose() {},
        };
      }
    </script>
  </body>
</html>
```

For fixed structure, put markup in the HTML body and styles in a style block or local stylesheet; Flux installs them before calling `mount`. Query those elements through `root` and bind editable text with `textContent`. Generate repeated or data-dependent elements when useful, but do not wrap an otherwise static document in a large JavaScript template string merely to initialize it. A local module can hold substantial animation logic separately. This keeps layout, animation and later text edits easier to change without nested string escaping.

Query and attach content through `root`, not the shared document body. Entry styles are scoped to the item. `render({ frame, progress, timeSeconds })` must synchronously reconstruct the requested frame, including backward and out-of-order seeks. Await asynchronous setup in `mount`. Pause GSAP timelines and seek them from supplied time; disable autonomous library tickers, D3 timers/transitions and animation loops. For p5, use instance mode, stop the automatic loop with `noLoop()` and draw the requested state explicitly. For Pixi, stop the ticker and render explicitly; for Lottie, disable autoplay and seek to the requested frame. Seed procedural randomness and derive it from stable inputs. Stop simulations and dispose owned resources in `dispose`. Precompute or deterministically reconstruct simulations instead of depending on previous playback frames. CSS `@import` and `url()` resources are unavailable.

## Embedding real media in Remotion

A visual reference and an image that must appear in the graphic are different requirements. For embedded project media, use the registered **asset ID** in Remotion `Img` or `Video` `src`; native SVG `<image href>` accepts the same media ID. The parent imports a local file with `push_asset` and supplies the returned ID. Do not substitute an invented drawing for required artwork, copy base64 image data into source, or use an inaccessible original filesystem path.

```tsx
import { Img } from "remotion";

export default function Graphic({ item }) {
  return (
    <Img
      src={item.props.imageId}
      style={{ width: 480, height: 320, objectFit: "contain" }}
    />
  );
}
```

Define `imageId` as an editable property with the actual imported ID as its default, or use the supplied ID directly when no control is required. `staticFile("image.png")` resolves relative to the MG entry directory; it only works when that file actually exists there. It does not download or import a reference. `Video` uses frame-based `trimBefore`/`trimAfter`, and `loop` requires `trimAfter`. Validate with the real binding and inspect native frames to verify that the image/video appears and its crop is correct; successful source compilation alone is insufficient.

## Editable property definitions

Pass matching definitions to validation/import. Types are UI property kinds, not JSON Schema or TypeScript types:

```json
[
  { "key": "title", "label": "Title", "type": "text", "defaultValue": "Hello" },
  {
    "key": "color",
    "label": "Color",
    "type": "color",
    "defaultValue": "#ffffff"
  }
]
```

Use the current tool/schema contract for other control types. Remotion reads resolved values from `item.props`; HTML reads `props` from `mount` and `update`. Confirm that edits reach the rendered output. Do not substitute a fallback that hides a disconnected control.

## Remotion modules and entry components

JavaScript/JSX and TypeScript/TSX are supported. Prefer an explicit default or
named export of the entry component; the entry module must have one unambiguous
export. Supporting modules may export reusable components and helpers.

Relative imports resolve within the MG source set, including `.tsx`, `.ts`,
`.jsx`, `.js`, `.json`, `.css`, and directory index files. Keep imports within
that source root and deliver all referenced files with the entry.

The current Remotion runtime registers `react`, `remotion`, `d3`, `p5`, `roughjs`, `paper`, `lottie-web`,
the registered MathJax modules, and
Remotion toolkit packages such as `@remotion/shapes`, `@remotion/paths`,
`@remotion/layout-utils`, `@remotion/animation-utils`, `@remotion/noise`,
`@remotion/rounded-text-box`, `@remotion/motion-blur`, `@remotion/lottie`, and `@remotion/gsap`.
Use `import * as d3 from "d3"`, not `import { d3 } from "remotion"`.
Prefer D3 calculations feeding React elements over competing DOM ownership.
Derive animation from `useCurrentFrame()`; p5 or other stateful drawing must
reconstruct that frame, clean up on unmount, and not run an independent clock.
The helpers below are convenience globals, not the complete package surface.
Verify import resolution and the intended API with native validation when using
another package or addon; do not reduce a library to a hand-maintained list of helpers.

## Entry props and editable values

Flux calls the exported entry with `{ item }`. Property definitions registered
with the asset supply defaults; instance overrides supply the edited values.
Read the resolved values from `item.props`. They are not spread onto the entry's
top-level props: `function Title({ title })` does not receive the editable title.

```tsx
import React from "react";
import { AbsoluteFill } from "remotion";

type TitleValues = { title: string; color: string };

export default function Title({ item }: { item: { props: TitleValues } }) {
  const { title, color } = item.props;
  return <AbsoluteFill style={{ color }}>{title}</AbsoluteFill>;
}
```

Register matching `title` and `color` property keys and their `defaultValue`
values. Pass these values explicitly to helper components. If a fallback is
needed, apply it after reading `item.props` and use `??` when empty text, zero,
or false is a valid user choice. Adding hardcoded defaults to an incorrectly
declared entry can make it visible while leaving its controls disconnected.

When creating or changing a property binding, check both the default output
and a visibly different override using the available preview tools. Successful
execution alone does not prove that a control affects the result. If override
rendering is unavailable, inspect the binding and report that limit rather than
claiming it was visually verified.

## Spring animation and diagnosis

Desktop's `spring({ frame, fps, config, from, to })` supports `from` and `to`,
defaulting to 0 and 1. For example, `from: 0.9, to: 1` is a valid scale animation;
mapping the default spring output with `0.9 + progress * 0.1` is also valid.
Use `useVideoConfig().fps` for the current composition's frame rate.

For missing text or unexpected geometry, inspect the actual property values
and animation output before attributing the failure to an API. Distinguish an
observed rendering problem from a suspected cause. If multiple changes fix the
image, do not claim one caused the failure without isolating it.

## Source delivery

Create source files in the active workspace and call `push_asset` with
`filePath` pointing to the entry module. Its exported component is the render
entry; relative imports resolve from the linked entry path. Keep the source
set available for playback/export. Importing creates an asset, while
`edit_item` places it on the timeline.

## Preloaded helpers

<!-- BEGIN generated:mg-injected-globals -->
<!-- Generated by scripts/gen-motion-graphic-globals.ts from Desktop's installed @chatcut/flux/motion-graphic-globals. Re-run: pnpm gen:motion-graphic-globals. DO NOT EDIT BY HAND. -->

These helpers are preloaded by the installed Desktop Flux runtime. This list describes convenience globals; it is not an import allowlist.

`AbsoluteFill`, `Arrow`, `Callout`, `CaptionText`, `Circle`, `createRoundedTextBox`, `culori`, `cutPath`, `d3`, `Easing`, `Ellipse`, `evolvePath`, `extendViewBox`, `fillTextBox`, `fitText`, `FitText`, `fitTextOnNLines`, `getBoundingBox`, `getLength`, `getPointAtLength`, `getSubpaths`, `getTangentAtLength`, `Heart`, `Icon`, `Img`, `interpolate`, `interpolateColors`, `interpolatePath`, `interpolateStyles`, `Loop`, `makeArrow`, `makeCallout`, `makeCircle`, `makeEllipse`, `makeHeart`, `makePie`, `makePolygon`, `makeRect`, `makeSpark`, `makeStar`, `makeTransform`, `makeTriangle`, `Math`, `measureText`, `noise2D`, `noise3D`, `noise4D`, `normalizePath`, `parsePath`, `Pie`, `Polygon`, `random`, `React`, `Rect`, `resetPath`, `reversePath`, `scalePath`, `Sequence`, `Series`, `Spark`, `spring`, `Star`, `staticFile`, `Trail`, `Transform`, `translatePath`, `Triangle`, `useCallback`, `useCurrentFrame`, `useEffect`, `useGsapTimeline`, `useLayoutEffect`, `useMemo`, `useRef`, `useState`, `useVideoConfig`, `Video`, `warpPath`

<!-- END generated:mg-injected-globals -->
