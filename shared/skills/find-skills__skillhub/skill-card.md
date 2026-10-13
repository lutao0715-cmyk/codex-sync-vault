## Description: <br>
Find Skills helps an agent match user requests to relevant installed, built-in, and marketplace skills, then recommend or install matching skills when the user confirms. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[guipi888](https://clawhub.ai/user/guipi888) <br>

### License/Terms of Use: <br>
MIT <br>


## Use Case: <br>
WorkBuddy and CodeBuddy users can use this skill to discover relevant agent skills from local directories, built-in skills, and external marketplaces. It is most useful when a user describes a task in natural language and wants ranked recommendations with installation options. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: This skill can search external marketplaces and send task descriptions to third-party services. <br>
Mitigation: Avoid sensitive task descriptions and review external search results before acting on them. <br>
Risk: This skill can use GitHub credentials and run commands such as downloads, git clone, npx, unzip, and writes into persistent skill directories. <br>
Mitigation: Use least-privilege credentials, require explicit user confirmation before installation, and review downloaded skill contents before enabling them. <br>
Risk: Recommended skills may come from third-party sources with different quality and security properties. <br>
Mitigation: Manually verify each source, scan installed skills, and prefer known local or built-in skills when they satisfy the request. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/guipi888/find-skills) <br>
- [Artifact README](artifact/README.md) <br>
- [Artifact skill definition](artifact/SKILL.md) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, shell commands, guidance] <br>
**Output Format:** [Markdown recommendations with inline shell commands and installation guidance] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [May include ranked skill recommendations, source labels, match rationale, paths, download or install commands, and follow-up prompts for user confirmation.] <br>

## Skill Version(s): <br>
1.0.0 (source: ClawHub release metadata; artifact frontmatter version is 1.7.0) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
