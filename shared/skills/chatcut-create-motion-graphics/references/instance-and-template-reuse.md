# Instance and template reuse

Read this before borrowing implementation code, reusing components or planning
a batch. Select and inspect the instances through
[step 3 of the main skill](../SKILL.md#3-inspect-instances).

## Use the references when authoring

Read the selected instance's `code` together with its saved property schema
and defaults when borrowing its implementation. Use `templateInspection` or
`manage_template list_assets` for template properties; `get` reads metadata
only. Use the source in the [main skill's code workflow](../SKILL.md#4-author-and-create-the-mg)
while preserving the project style. Adapt the code and schema together, and
resolve embedded media to current-project assets as described in
[Media and MG composition](media-composition.md). A template asset ID or code
snapshot is not an editable asset in the current project.

## Plan a related batch

Before authoring a batch, map each MG's viewer job, actual content, chosen form,
target shot, speech span, reading time and internal motion beats. Mark which
forms intentionally recur. An accepted direction defines the visual language;
it does not make one layout suitable for every moment.

For a new custom direction, create and check one composed result before
expanding it across the video. Reuse one asset with item-level properties only
when the viewer job, information structure and visual form recur. Use distinct
assets when those differ, while keeping typography, palette, materials and
motion coherent. A shared color or card treatment alone is not a reuse reason.
