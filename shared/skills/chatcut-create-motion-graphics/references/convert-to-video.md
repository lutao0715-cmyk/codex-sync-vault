# Convert an MG to Video

Use this workflow when the user wants an existing MG as a reusable transparent
video asset in the Desktop media pool. Desktop renders locally; follow the
`local_export` tool description for parameters and return data.

1. **Export the MG** — use `local_export` with `format: "motion_graphic"`.
   Select the media-pool MG with `motionGraphicAssetId`, or an exact timeline
   instance with `motionGraphicItemId` to include its edits. The output is a
   transparent ProRes 4444 `.mov`; MG export requires ChatCut Pro.
2. **Wait for completion** — the tool returns `outputPath` and `taskId` after
   queuing the render. Check completion in Export History before importing;
   a returned path does not mean the file is ready.
3. **Import the video** — use `push_asset` with the completed `outputPath` to
   add the video to the local media pool.
4. **Place or replace** — use `edit_item` with the imported asset ID. When
   replacing an MG item, preserve its placement, start and duration; adjust
   playback rate if needed to keep the same timeline span. Verify transparency
   and the complete composition in the timeline viewer.

This workflow uses local export and import, not cloud render IDs or
`register_converted_video`.
