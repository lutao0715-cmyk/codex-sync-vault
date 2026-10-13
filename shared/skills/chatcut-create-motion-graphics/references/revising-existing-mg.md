# Patch An Existing Asset

For property, placement or localized source changes, reuse the accepted style
and references; no new style selection or catalog scan is needed.

Route an existing-MG change before choosing tools:

1. Position, size, timing, crop, or layer order of one placed instance: use `edit_item`. Do not read source code.
2. Text, color, font, media, boolean, or numeric value already exposed by the asset schema: use `edit_item propertyOverrides` for one instance or `edit_asset propertyDefaults` for the asset default. Do not read source code.
3. Internal animation, easing, layout, element order, or a new editable property: use the Desktop workspace-file workflow below.
4. A fundamentally different visual mechanism, information structure, or overall design: create a new direct-authored asset rather than forcing the old structure to fit.

For a linked multi-file MG whose source you are already editing, keep the entry
and relative module layout together, edit those files in place, and verify the
linked asset on the timeline. Submitting a copied entry alone does not copy its
siblings. Use the following workspace-copy workflow for single-file assets.

Desktop workspace-file workflow:

1. Call `inspect_asset` with the MG `assetId` and `includeCodeFile:true`. It materializes the source in the active Desktop agent workspace and returns its path, byte size, and property schema without putting source in the tool result.
2. Read the returned path once, then use native `Edit` for the smallest localized source change while preserving unrelated behavior, property keys, and timeline timing.
3. Call `edit_asset` with `action=update`, the same `assetId`, and `codeFile`. Do not put the full source in `json.code`; ChatCut Desktop reads the workspace file directly. This adapter reads one file; sibling modules need a source-set-aware submission path or a self-contained module.
4. If the source has changed since inspection, materialize it again and reapply the localized change instead of overwriting newer edits.
5. Re-read asset state and use `preview_timeline` with the viewer view for entry, settled state, and exit before claiming the visual change is complete.

When exposing a new editable value, update its code and property schema in the
same call; preserve existing keys and defaults, and migrate item overrides if
a key must change. A per-item override cannot introduce a schema key. Expose
missing text/font/color/transparency controls instead of hardcoding them.

When replacing an MG on the timeline, keep the previously accepted asset
in the media pool unless the user requested cleanup.
