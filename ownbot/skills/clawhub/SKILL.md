---
name: clawhub
description: Search and install agent skills from ClawHub, the public skill registry.
homepage: https://clawhub.ai
metadata: {"nanobot":{"emoji":"🦞"}}
---
# ClawHub

Public skill registry for AI agents. Search by natural language (vector search).

## When to use

Use this skill when the user asks any of:

- "find a skill for …"
- "search for skills"
- "install a skill"
- "what skills are available?"
- "update my skills"

## Search

```bash
npx --yes clawhub@latest search "web scraping" --limit 5
```

## Install

```bash
npx --yes clawhub@latest install <slug> --workdir ~/.ownbot/workspace
```

Replace `<slug>` with the skill name from search results. This places the skill into `~/.ownbot/workspace/skills/`, where ownbot loads workspace skills from. Always include `--workdir`.

After a successful install, rebuild OwnBot's workspace skill index:

```bash
ownbot index-skills --force
```

## Update

```bash
npx --yes clawhub@latest update --all --workdir ~/.ownbot/workspace
```

After updating workspace skills, rebuild the index:

```bash
ownbot index-skills --force
```

## List installed

```bash
npx --yes clawhub@latest list --workdir ~/.ownbot/workspace
```

## Notes

- Requires Node.js (`npx` comes with it).
- No API key needed for search and install.
- Login (`npx --yes clawhub@latest login`) is only required for publishing.
- `--workdir ~/.ownbot/workspace` is critical — without it, skills install to the current directory instead of the ownbot workspace.
- After install or update, run `ownbot index-skills --force` so workspace skills are immediately searchable.
- Starting a new conversation is still helpful so the model gets a fresh system prompt that includes any newly retrievable workspace skills.
