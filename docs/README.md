# FastBlocks Documentation

This directory contains technical documentation, guides, and examples for FastBlocks development.

## Documentation Structure

### Main Documentation (Root Level)

- **[README.md](../README.md)** - Comprehensive project README with installation, quick start, and API reference
- **[CLAUDE.md](../CLAUDE.md)** - AI agent development guide (primary reference for Claude Code)
- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Repository guidelines for contributors
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes

### Technical Guides (docs/)

#### ACB Integration

- **[ACB_GUIDE.md](ACB_GUIDE.md)** - Complete guide to using Asynchronous Component Base (ACB) with FastBlocks
  - ACB Actions (compression, hashing, encoding, security, validation)
  - ACB Adapters (database, cache, storage, monitoring)
  - Configuration examples and best practices
  - Migration guide from custom implementations to ACB

#### Template System

- **[JINJA2_ASYNC_ENVIRONMENT_USAGE.md](JINJA2_ASYNC_ENVIRONMENT_USAGE.md)** - Technical guide for jinja2-async-environment integration
  - Template inheritance patterns
  - Async rendering implementation
  - Block rendering for HTMX integration

### Version Migration (docs/migrations/)

- **[MIGRATION-0.17.0.md](migrations/MIGRATION-0.17.0.md)** - Migration guide for v0.17.0
  - Dependency groups migration (PEP 735)
  - Breaking changes and upgrade instructions

### Examples (docs/examples/)

- **[TEMPLATE_EXAMPLES.md](examples/TEMPLATE_EXAMPLES.md)** - Template usage examples and patterns

### Archived Documentation (docs/archive/)

Historical documentation preserved for reference:

- Consolidated AI agent docs (QWEN.md, GEMINI.md)
- Consolidated ACB documentation
- Historical quality and incident reports

See [docs/archive/README.md](archive/README.md) for details.

## Quick Reference

### For New Contributors

1. Start with [CONTRIBUTING.md](../CONTRIBUTING.md) for repository guidelines
1. Read [README.md](../README.md) for project overview and quick start
1. Review [CLAUDE.md](../CLAUDE.md) if using AI assistance

### For ACB Integration

1. Read [ACB_GUIDE.md](ACB_GUIDE.md) for comprehensive ACB usage
1. Use ACB actions for utilities (hashing, compression, encoding)
1. Use ACB adapters for infrastructure (database, cache, storage)

### For Template Development

1. Review template examples in [examples/TEMPLATE_EXAMPLES.md](examples/TEMPLATE_EXAMPLES.md)
1. Understand async patterns in [JINJA2_ASYNC_ENVIRONMENT_USAGE.md](JINJA2_ASYNC_ENVIRONMENT_USAGE.md)
1. Use `[[` `]]` delimiters (not `{{` `}}`)

### For Version Migration

Check [migrations/](migrations/) for version-specific upgrade guides.

## Documentation Standards

### File Naming

- Use `SCREAMING_SNAKE_CASE` for major guides (e.g., ACB_GUIDE.md)
- Use `kebab-case` for specific documents (e.g., pre-commit-resolution.md)
- Use descriptive names that indicate content

### Content Structure

- Start with a clear title and overview
- Include table of contents for long documents
- Use code examples with language tags
- Link to related documentation
- Update CHANGELOG.md for significant changes

### Markdown Style

- Use ATX-style headers (`#` not underlines)
- Include blank lines around code blocks
- Use backticks for inline code
- Use triple backticks with language for code blocks
- Use tables for comparisons and reference data

## Maintenance

### Regular Reviews

Documentation should be reviewed:

- When adding new features
- During major version updates
- When deprecating functionality
- Quarterly for accuracy and relevance

### Archival Criteria

Archive documentation when:

- Content is superseded by newer documentation
- Information is purely historical
- Content is redundant with active documentation

Move archived files to `docs/archive/` with explanation in `docs/archive/README.md`.

## Contributing to Documentation

When updating documentation:

1. Follow the documentation standards above
1. Update related cross-references
1. Test all code examples
1. Run markdown linters
1. Include changes in pull request description

For major documentation restructuring, open an issue for discussion first.

## Questions?

For documentation questions or suggestions:

- Open an issue on GitHub
- Reference the specific documentation file
- Suggest improvements with examples

______________________________________________________________________

**Last Updated**: 2025-11-18
**Documentation Version**: 2.0 (Post-consolidation)
