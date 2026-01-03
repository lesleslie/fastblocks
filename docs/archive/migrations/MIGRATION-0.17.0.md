# Migration Guide: Dependency Groups Modernization (v0.17.0)

## Breaking Change

FastBlocks v0.17.0 migrates from `[project.optional-dependencies]` to `[dependency-groups]` following **PEP 735** and modern UV standards.

## What Changed

### Old Syntax (No Longer Works)

```bash
# ❌ These commands will fail
uv add "fastblocks[admin]"
uv add "fastblocks[monitoring]"
uv add "fastblocks[admin,monitoring,sitemap]"
```

### New Syntax

```bash
# ✅ Use these instead
uv add --group admin
uv add --group monitoring
uv add --group admin --group monitoring --group sitemap
```

## Why This Change?

1. **PEP 735 Compliance**: Modern standard for dependency groups
1. **Consistency**: Aligns with ACB v0.24.0+ modernization
1. **UV Compatibility**: Full support for latest UV features
1. **Better Organization**: Clear categorization of dependencies

## Migration Steps

### 1. Update Installation Commands

#### Feature Groups

```bash
# Admin interface (SQLAdmin)
uv add --group admin

# Monitoring (Logfire + Sentry)
uv add --group monitoring

# Sitemap generation
uv add --group sitemap

# Multiple features at once
uv add --group admin --group monitoring
```

#### Development

```bash
# Development tools
uv add --group dev
```

### 2. Update CI/CD Pipelines

**Before**:

```yaml
- name: Install FastBlocks with features
  run: uv add "fastblocks[admin,monitoring]"
```

**After**:

```yaml
- name: Install FastBlocks with features
  run: uv add --group admin --group monitoring
```

### 3. Reinstall Dependencies

After upgrading to v0.17.0:

```bash
# Remove old installation
uv remove fastblocks

# Install core FastBlocks
uv add fastblocks

# Add your required feature groups
uv add --group admin --group monitoring
```

## Dependency Group Details

### Admin Group

```bash
uv add --group admin
```

**Includes**: sqladmin>=0.21

**Use for**: Adding web-based admin interface to your FastBlocks application

### Monitoring Group

```bash
uv add --group monitoring
```

**Includes**:

- logfire[starlette]>=3.24
- sentry-sdk[starlette]>=2.32
- urllib3>=2.5

**Use for**: Production monitoring, error tracking, and observability

### Sitemap Group

```bash
uv add --group sitemap
```

**Includes**: (Currently empty - sitemap generation uses core dependencies)

**Use for**: SEO sitemap generation

## Troubleshooting

### Error: "Unknown extra: admin"

**Problem**: Using old extras syntax

```bash
uv add "fastblocks[admin]"  # ❌ Fails
```

**Solution**: Use new dependency group syntax

```bash
uv add --group admin  # ✅ Works
```

### Multiple Groups Installation

**Preferred approach**:

```bash
uv add --group admin --group monitoring
```

**Alternative** (one at a time):

```bash
uv add --group admin
uv add --group monitoring
```

## Benefits

1. **Modern Standards**: Aligned with PEP 735 and UV best practices
1. **Cleaner Dependencies**: No circular references
1. **Better Control**: Explicitly choose what features you need
1. **Future-Proof**: Matches direction of Python packaging ecosystem

## Questions?

- See [README.md](../../README.md) for updated installation examples
- Check [CHANGELOG.md](../../CHANGELOG.md) for detailed release notes
- Review [CLAUDE.md](../../CLAUDE.md) for development guidelines

## Migration Checklist

- [ ] Updated installation commands to use `--group` syntax
- [ ] Updated CI/CD pipelines
- [ ] Reinstalled dependencies with new syntax
- [ ] Verified application still works

______________________________________________________________________

**Version**: 0.17.0
**Migration Difficulty**: Low (syntax change only)
**Estimated Time**: 5 minutes
