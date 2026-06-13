# FastBlocks Admin Shell

The FastBlocks admin shell provides an interactive IPython shell for FastBlocks application development with built-in session tracking via Session-Buddy.

## Features

### Builder Commands

- **`build()`** - Build application and return build info
- **`render()`** - Get template rendering info
- **`routes()`** - Show routing table
- **`auth`** - Authentication configuration info

### Session Tracking

The admin shell automatically tracks sessions via Session-Buddy:

- Tracks shell session lifecycle (start/end)
- Records component metadata (version, adapters)
- Fire-and-forget emission for non-blocking startup
- Session duration tracked automatically

## Usage

### Starting the Shell

```bash
cd your-fastblocks-app
fastblocks shell
```

### Example Session

```python
FastBlocks Admin Shell
============================================================
Application Builder & Web Framework
Version: 0.19.0

Adapters: web_framework, ui_components
Session Tracking: ✓ Enabled

Builder Commands:
  build()        - Build application
  render()       - Render templates
  routes()       - Show routing table
  auth           - Authentication info

Type 'help()' for Python help or %help_shell for shell commands
============================================================

In [1]: build()
Out[1]:
{'status': 'success',
 'app_name': 'My App',
 'middleware_count': 5}

In [2]: routes()
Out[2]:
[{'path': '/', 'name': 'index', 'methods': ['GET', 'POST']},
 {'path': '/about', 'name': 'about', 'methods': ['GET']}]

In [3]: auth
Out[3]:
{'enabled': True, 'type': 'basic', 'csrf_enabled': True}

In [4]: render()
Out[4]:
{'status': 'success',
 'templates': {'loader': 'FileSystemLoader',
               'auto_reload': True,
               'cache_size': 100}}
```

## Programmatic Usage

You can also use the shell programmatically:

```python
from fastblocks.shell import FastBlocksShell
from fastblocks.applications import FastBlocks

app = FastBlocks()
shell = FastBlocksShell(app)
shell.start()
```

## Session Tracking

### Component Metadata

The shell tracks the following metadata for each session:

- **Component name**: "fastblocks"
- **Component version**: FastBlocks package version
- **Adapters**: List of enabled adapters (web_framework, ui_components, etc.)
- **Shell type**: "FastBlocksShell"

### Session Events

- **Session Start**: Emitted when shell starts (fire-and-forget, non-blocking)
- **Session End**: Emitted when shell exits (via atexit handler)
- **Duration**: Calculated automatically by Session-Buddy

### Configuration

Session tracking is automatically enabled if Session-Buddy MCP server is available. No additional configuration is required.

## Architecture

The FastBlocksShell extends the Oneiric AdminShell base class, providing:

- **Namespace helpers**: FastBlocks-specific commands and utilities
- **Session tracking**: Automatic session lifecycle tracking
- **Banner**: Customized banner with component info
- **IPython integration**: Full IPython shell with magics and autocomplete

## Testing

Run the shell tests:

```bash
pytest tests/shell/test_shell_adapter.py -v
```

## Requirements

- IPython (installed automatically with Oneiric)
- Oneiric >= 0.3.4
- Session-Buddy (optional, for session tracking)
