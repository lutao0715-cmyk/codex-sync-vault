# Flux/Blink HTML pixel processor contract

This is the HTML runtime contract, not the Web shader processor contract. HTML uses DOM image inputs; it does not provide `inputTexture`, `outgoingTexture`, or a shader `renderPass` context.

## Lifecycle and inputs

- Effect: `export default function mount({root, input, props, timeline, viewport})`.
- Transition: `export default function mount({root, outgoing, incoming, props, timeline, viewport})`.
- Return a controller (or a Promise for one) with `render({frame, progress, timeSeconds})`, `dispose()`, and optionally `update({props, revision})`.
- `viewport.width` / `height` are the actual input dimensions. `timeline` supplies `fps`, `durationInFrames`, and `durationInSeconds`. Frame and time are local to the effect/transition. Progress spans its duration.
- Inputs are host-owned `HTMLImageElement`s, refreshed before each `render`, and invalid during `mount`. They are hidden outside `root`. Draw them with Canvas `drawImage`; never remove them, set `src`, change their attributes, or replace current input with an earlier snapshot.
- Only the authored `root` is captured. Query within `root`, size output to the viewport, and draw the input explicitly when it should remain visible.
- Reconstruct each frame from the supplied time/progress. Avoid accumulated transforms, wall-clock time, requestAnimationFrame loops, unseeded randomness, or playback-history dependence. Seeking backward must reproduce the same image.
- Use `update` for resolved properties. Mount receives an initial object that must not be relied on for all later values.
- Inputs/output are encoded SDR sRGB. HTML processors do not declare native processing capabilities.

## Organizing the implementation

The examples below are deliberately compact demonstrations of the lifecycle, not a preferred visual style or a requirement to use one file. For a larger processor, keep the HTML entry readable and move independent responsibilities into focused local files. “Self-contained” means the resource directory contains its dependencies; use the local module support described below rather than packing everything into the entry.

## Canvas effect entry

This minimal example modifies live input saturation. Use it as a structural reference for more distinctive visual treatments.

```html
<!doctype html>
<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
</style>
<canvas></canvas>
<script type="module">
  export default function mount({ root, input, viewport }) {
    const canvas = root.querySelector("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D unavailable");
    let strength = 0.25;
    return {
      update({ props }) {
        strength = Math.max(0, Math.min(1, Number(props.strength ?? 0.25)));
      },
      render({ timeSeconds }) {
        const { width, height } = canvas;
        ctx.resetTransform();
        ctx.clearRect(0, 0, width, height);
        ctx.save();
        ctx.filter = `saturate(${1 + strength})`;
        ctx.drawImage(input, 0, 0, width, height);
        ctx.restore();
      },
      dispose() {
        canvas.remove();
      },
    };
  }
</script>
```

## Two-input transition entry

This example wipes to the incoming frame. Clear inside the clipped incoming area so input alpha remains correct. Progress zero is exactly outgoing; one is exactly incoming.

```html
<!doctype html>
<style>
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
</style>
<canvas></canvas>
<script type="module">
  export default function mount({ root, outgoing, incoming, viewport }) {
    const canvas = root.querySelector("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D unavailable");
    return {
      render({ progress }) {
        const { width, height } = canvas;
        const p = Math.max(0, Math.min(1, progress));
        const eased = p * p * (3 - 2 * p);
        ctx.resetTransform();
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(outgoing, 0, 0, width, height);
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, 0, width * eased, height);
        ctx.clip();
        ctx.clearRect(0, 0, width, height);
        ctx.drawImage(incoming, 0, 0, width, height);
        ctx.restore();
      },
      dispose() {
        canvas.remove();
      },
    };
  }
</script>
```

## DOM, modules and WebGL

The entry contains markup, scoped styles and exactly one module script, inline or referencing a local path. Local JS/TS, JSON, CSS and GLSL imports resolve within the resource directory; relative GLSL imports yield source strings. Bare imports must come from the bundled HTML module registry (for example Three.js or GSAP); arbitrary npm, remote scripts and remote stylesheets are unavailable. Bundle local assets beside the entry and avoid runtime network dependencies.

DOM overlays, clipping, Canvas 2D and WebGL may be combined within the root. Native image inputs have no ordinary response URL and cannot be passed directly to `gl.texImage2D`. For WebGL, draw each live input to a staging Canvas during every render, then upload that Canvas as the texture source. Transitions need separate staging surfaces for their two inputs. Reuse allocations; release owned GL textures, programs, buffers and listeners in `dispose`.

If using an animation library, keep it paused and seek it to the supplied frame/time. Native mounting/font readiness can be asynchronous; return the mount Promise rather than drawing before resources are ready. Throw actionable errors on initialization failure rather than silently producing a blank frame.
