# FastBlocks Admin Shell - Quick Reference

## Installation

No additional installation required. The admin shell is included with FastBlocks.

## Starting the Shell

```bash
cd your-fastblocks-app
fastblocks shell
```

## Available Commands

### `build()`

Build the application and return build information.

```python
In [1]: build()
Out[1]:
{'status': 'success',
 'app_name': 'My App',
 'middleware_count': 5}
```

### `render()`

Get template rendering configuration.

```python
In [2]: render()
Out[2]:
{'status': 'success',
 'templates': {'loader': 'FileSystemLoader',
               'auto_reload': True,
               'cache_size': 100}}
```

### `routes()`

List all application routes.

```python
In [3]: routes()
Out[3]:
[{'path': '/', 'name': 'index', 'methods': ['GET', 'POST']},
 {'path': '/about', 'name': 'about', 'methods': ['GET']}]
```

### `auth`

View authentication configuration.

```python
In [4]: auth
Out[4]:
{'enabled': True, 'type': 'basic', 'csrf_enabled': True}
```

## Session Tracking

The shell automatically tracks sessions via Session-Buddy:

- Session start/end events emitted automatically
- Component metadata recorded (version, adapters)
- Non-blocking emission for fast startup

## Python Shell Features

All standard Python/IPython features available:

- `help()` - Python help
- `?` - Object documentation
- `tab` - Autocomplete
- `!command` - Shell commands
- `%magic` - IPython magics

## Programmatic Usage

```python
from fastblocks.shell import FastBlocksShell
from fastblocks.applications import FastBlocks

app = FastBlocks()
shell = FastBlocksShell(app)
shell.start()
```

## Namespace Objects

- `app` - FastBlocks application instance
- `asyncio` - Asyncio module
- `run` - Alias for `asyncio.run()`
- `logger` - Logger instance
- `Console` - Rich console (from rich.console)
- `Table` - Rich table (from rich.table)
- `build` - Build helper function
- `render` - Render helper function
- `routes` - Routes helper function
- `auth` - Authentication info dict

## Troubleshooting

### "No main.py found in current directory"

Make sure you're in a FastBlocks project directory with a `main.py` file.

### "No 'app' object found in main.py"

Your `main.py` should expose an `app` object:

```python
# main.py
from fastblocks.applications import FastBlocks

app = FastBlocks()
```

### Session tracking not working

Session tracking requires Session-Buddy MCP server to be running. It's optional - the shell will work without it.

## More Information

See `/Users/les/Projects/fastblocks/docs/ADMIN_SHELL.md` for full documentation.
