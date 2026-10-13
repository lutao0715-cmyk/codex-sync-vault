---
name: skill-creator
description: |
  Create or update reusable ChatCut Workflow Skills from completed or clearly validated editing
  conversations/projects. Use only when the user explicitly asks to save, remember, codify, create,
  update, or reuse an editing process as a skill, or when the UI prompt asks to save this editing
  process as a Skill. Do not use for ordinary editing tasks that only need the current video edited.
user-invocable: false
---

# ChatCut Skill Creator

This skill turns a proven ChatCut editing approach into a user-owned Workflow Skill.

A Workflow Skill should help the agent repeat an editing method later. It should not be a chat
transcript, a frozen tool-call recipe, or a bundle of fragile internal parameters.

## Decide Whether to Save Now

Use judgment from the current conversation and project state.

- Save only from a completed, user-approved, or clearly validated workflow.
- If the user is only describing a desired skill, rough idea, or unfinished process, do not save yet.
  Help them run the workflow or collect enough detail first.
- If key details are missing, ask focused follow-up questions until the reusable workflow would be
  accurate. Do not optimize for one-turn creation.
- If the edit is just starting, still experimental, or has no stable outcome yet, tell the user the
  workflow can be saved after the edit is finished or the successful approach is clearer.
- Before calling `manage_skill`, recap the proposed skill name, use case, workflow, principles, and
  checks, then ask the user to confirm. Save only after that confirmation, unless the user already
  confirmed those exact details.
- If the user is correcting an existing skill, update that skill instead of creating a duplicate.

Do not change the timeline, assets, captions, design style, or generated media while creating a
skill. This workflow is for capturing knowledge, not editing the video.

## What to Capture

Capture durable editing intent and process:

- When this skill should be used, in the user's own editing language.
- Inputs the agent should look for, such as source footage type, target platform, target length,
  brand/design style, references, script, product info, or examples.
- The repeatable workflow steps, from understanding the source through final QA.
- Preferences the user validated, such as pacing, structure, caption style, B-roll taste, MG density,
  tone, checkpoints, export expectations, or recurring wording.
- Rules that prevent common mistakes for this user's workflow.
- Quality checks that the agent can apply before saying the edit is done.
- Lightweight reusable references only when useful. Stable official or product-managed ids are OK
  when they are meant to travel across projects, such as design styles, templates, voice presets,
  or other curated presets.
- Do not save project media asset ids in user skills; describe reusable asset taste or source
  expectations in normal editing language instead.

Avoid capturing:

- Low-level tool parameters, transient item ids, segment ids, clip ids, timestamps, or implementation
  details that may change as ChatCut evolves.
- Project media asset ids or heavyweight asset references. They are usually project-scoped and may
  not resolve in future projects.
- Private chat dumps, credentials, unrelated personal context, or one-off project details.
- Claims that the workflow always performs better than alternatives unless the user actually
  validated that.
- Overly broad trigger language that would make the skill fire for unrelated edits.

## Skill Shape

Create a standard Skill package in the Desktop workspace, then save it with `manage_skill`.

Minimum package:

```text
SKILL.md
```

Optional lightweight files, only when they reduce clutter or add reusable detail:

```text
references/...
examples/...
scripts/...
```

Use one `SKILL.md` for simple workflows. Add `references/` for deeper guidance, `examples/` for
compact good/bad examples, and `scripts/` only for lightweight helpers that complement ChatCut
rather than duplicate its editing, download, transcode, or export tools.

In `SKILL.md`, use normal Claude skill conventions:

- Frontmatter `name` and `description`.
- A clear H1 title for the user-facing skill name.
- Short sections for when to use it, needed inputs, workflow, preferences/rules, and final checks.
- Links to optional files, so they load progressively only when useful.

These are guidance lenses, not a required schema. Include only what makes the workflow stable and
reproducible.

## Writing Guidelines

- Name the skill after the user's reusable outcome, not the current project title unless the project
  title is the recurring format.
- Keep the description short enough to scan in the skill list.
- Use normal editing language. Prefer "cut the strongest hook first" over internal command names.
- Preserve useful style/template concepts, but leave room for the current ChatCut tools to evolve.
- Be specific enough to guide future work, but not so specific that the skill only fits one old
  source video.
- If there are several distinct workflows in the conversation, save the one the user asked about; do
  not merge unrelated workflows into one vague skill.

## After Saving

Save with `manage_skill` after the package files are written:

```text
manage_skill({
  action: "create_from_directory",
  sourceDirectory: ".chatcut/skill-drafts/<slug>",
  name: "<user-facing skill name>"
})
```

For an existing skill, call `manage_skill({ action: "get", agentSkillId })`, recreate the returned
package in `.chatcut/skill-drafts/<slug>`, edit it, then call:

```text
manage_skill({
  action: "update_from_directory",
  agentSkillId: "<skill id>",
  sourceDirectory: ".chatcut/skill-drafts/<slug>"
})
```

After saving, reply with a concise plain-language recap:

- Skill name
- When to use it
- Core editing steps
- Important preferences/rules/checks
- Where to reuse it: tell the user they can select saved Skills from the book icon below the chat
  input, or ask the agent by name so it can find the Skill with `manage_skill`.

If the user corrects anything later, update the same skill.
