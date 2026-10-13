# Flux Web Audio module contract

Effects default-export `mount({context, input, output, properties})`. Transitions default-export `mount({context, outgoing, incoming, output, properties})`.

- `context` is the host's `OfflineAudioContext`; input/output values are supplied `AudioNode`s, not samples, textures or DOM images.
- Mount synchronously builds and connects the graph. It must return `undefined`, not a Promise, controller or cleanup function. The runtime owns teardown and recreates the instance after seek, model replacement or output-format changes.
- Connect the supplied inputs to `output`. Do not create an AudioContext or connect to a device/destination yourself.
- `properties` is a frozen object containing defaults and overrides. Do not mutate it. Audio editable property types are `number`, `boolean`, and `select`.
- Prefer native Web Audio nodes. The bundled registry includes Tone.js; arbitrary npm, network imports, DOM/Canvas and HTML entries are not the audio contract. Use a self-contained module; do not assume the HTML local-module resolver is available.
- Bound filter frequencies below `context.sampleRate / 2`, feedback below unity, and output gain to a controlled range. Account for DC, clipping and silence. Do not market a compressor as a true-peak limiter or an EQ as AI speech denoising.
- Item effects process that item's signal before its track bus. Track and master effects process their summed signal and silent blocks while the timeline renders. Effects are ordered by `sortOrder`, then ID.

## Example: band-limited dialogue

```ts
export default function mount({ context, input, output, properties }) {
  const highpass = context.createBiquadFilter();
  highpass.type = "highpass";
  highpass.frequency.value = Math.min(context.sampleRate * 0.45, 300);
  highpass.Q.value = 0.707;
  const lowpass = context.createBiquadFilter();
  lowpass.type = "lowpass";
  lowpass.frequency.value = Math.max(
    20,
    Math.min(context.sampleRate * 0.45, Number(properties.cutoff ?? 3200)),
  );
  lowpass.Q.value = 0.707;
  input.connect(highpass);
  highpass.connect(lowpass);
  lowpass.connect(output);
}
```

## Transition timing and seeks

Transitions receive two stereo signals after item effects and before track effects. Their duration is centered on the adjacent cut and requires source handles. The host augments properties with `transitionStartSeconds`, `transitionDurationSeconds`, and `projectTimeSeconds` in root timeline seconds. `projectTimeSeconds` is the graph's first sample position, including a seek or export starting inside the transition.

Convert authored timeline times to graph-local seconds by subtracting that initial `projectTimeSeconds`. Evaluate the starting gain at that position before scheduling future automation. Do not start from outgoing gain 1 on every mount.

```ts
export default function mount({
  context,
  outgoing,
  incoming,
  output,
  properties,
}) {
  const start = Number(properties.transitionStartSeconds);
  const duration = Number(properties.transitionDurationSeconds);
  const now = Number(properties.projectTimeSeconds);
  if (![start, duration, now].every(Number.isFinite) || duration <= 0)
    throw new Error("Invalid audio transition timing");
  const gainAt = (time, incomingSide) => {
    const p = Math.max(0, Math.min(1, (time - start) / duration));
    return incomingSide
      ? Math.sin((p * Math.PI) / 2)
      : Math.cos((p * Math.PI) / 2);
  };
  for (const [source, incomingSide] of [
    [outgoing, false],
    [incoming, true],
  ]) {
    const gain = context.createGain();
    gain.gain.setValueAtTime(gainAt(now, incomingSide), 0);
    const from = Math.max(now, start);
    const end = start + duration;
    if (from > now)
      gain.gain.setValueAtTime(gainAt(from, incomingSide), from - now);
    if (end > from) {
      const curve = Float32Array.from({ length: 257 }, (_, i) =>
        gainAt(from + ((end - from) * i) / 256, incomingSide),
      );
      gain.gain.setValueCurveAtTime(curve, from - now, end - from);
    }
    source.connect(gain);
    gain.connect(output);
  }
}
```

Equal-power crossfades suit uncorrelated signals; identical/correlated signals can gain level in the middle. Choose constant-gain curves when preserving that level is the intended result. Do not add a gain boost merely to make the processed example sound better.
