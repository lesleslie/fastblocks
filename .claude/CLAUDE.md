# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Agent Discovery Configuration

This project has access to **specialized AI agents** from two locations:

1. **Local agents**: `/Users/les/Projects/fastblocks/.claude/agents/`
   - FastBlocks-stack specialists: `web-components-specialist`, `pwa-specialist`,
     `htmx-specialist`, `htmy-specialist`, `fastblocks-specialist`
1. **Global agents**: `/Users/les/.claude/agents/`
   - Bodai ecosystem specialists + mycelium-core plugins (loaded automatically
     via `.claude/settings.local.json#permissions.additionalDirectories`)

This project has no per-repo overrides for skills or commands — those use the
global `/Users/les/.claude/skills/` and `/Users/les/.claude/commands/`.

### How to Use Agents

**Via Task tool:**

```
Use the Task tool with subagent_type="agent-name"
Example: subagent_type="htmx-specialist" for HTMX hypermedia patterns
Example: subagent_type="fastblocks-specialist" for FastBlocks framework work
```

**Via /agents Command:**
Run `/agents` in Claude Code to browse all available agents interactively.

### FastBlocks-stack Specialists (this project)

| Agent | Trigger |
|---|---|
| `web-components-specialist` | Custom Elements, Shadow DOM, HTML templates, slots |
| `pwa-specialist` | Service workers, manifest.json, offline-first, install prompts |
| `htmx-specialist` | HTMX attributes (hx-get/post/swap), hypermedia patterns |
| `htmy-specialist` | HTMY Python components, template bridges, adapter design |
| `fastblocks-specialist` | FastBlocks adapters, template blocks, ACB, Starlette routes |

### Tools & Workflows

- **49 Development Tools**: Located in `.claude/commands/tools/` (symlinked)
- **15 Multi-Agent Workflows**: Located in `.claude/commands/workflows/` (symlinked)

Use `/workflows:WORKFLOW-CATALOG` to discover the right workflow for any task.

### Troubleshooting

If agents are not discovered:

1. Check that local agents dir exists at `/Users/les/Projects/fastblocks/.claude/agents/`
1. Verify global agents dir is readable at `/Users/les/.claude/agents/`
1. Verify `additionalDirectories` includes `/Users/les/.claude` in `.claude/settings.local.json`
1. Run `/agents` command to refresh agent list
1. Restart Claude Code session if needed

For more details, see `/Users/les/.claude/CLAUDE.md`
