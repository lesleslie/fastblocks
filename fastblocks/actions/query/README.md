# Universal Query Actions

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../../README.md) | [Actions](../README.md) | [Adapters](../../adapters/README.md)

Actions for converting HTTP request query parameters into ACB universal database queries.

## Features

- **Automatic Query Parameter Parsing**: Converts URL query parameters to database queries
- **Multiple Filter Operators**: Support for equals, gt, lt, contains, in, null, etc.
- **Pagination Support**: Built-in page/limit parameter handling
- **Sorting**: Order by any field with asc/desc direction
- **ACB Integration**: Works with all ACB query patterns (simple, repository, specification, advanced)
- **Template Context**: Provides ready-to-use context for templates

## Usage

### Basic Query Parsing

```python
from fastblocks.actions.query import UniversalQueryParser

# In your endpoint
parser = UniversalQueryParser(request, User)
results = await parser.parse_and_execute()
```

### Template Context Creation

```python
from fastblocks.actions.query import create_query_context

# Create context with query results
context = create_query_context(request, "user", {"page": "users"})
```

### URL Query Examples

```
# Basic filtering
/users?active=true&age__gt=18

# Pagination
/users?page=2&limit=20

# Sorting
/users?order_by=created_at&order_dir=desc

# Complex queries
/users?department__in=engineering,design&salary__gte=50000&order_by=name&page=1
```

## Supported Operators

- `field=value` - Equals
- `field__gt=value` - Greater than
- `field__gte=value` - Greater than or equal
- `field__lt=value` - Less than
- `field__lte=value` - Less than or equal
- `field__contains=value` - Contains (LIKE %value%)
- `field__icontains=value` - Case-insensitive contains
- `field__in=val1,val2` - In list
- `field__not=value` - Not equals
- `field__null=true/false` - Is null/not null

## Integration with Endpoints

The query actions are designed to work seamlessly with FastBlocks endpoints:

```python
class Index(FastBlocksEndpoint):
    async def get(self, request: HtmxRequest) -> Response:
        context = create_query_context(request, base_context={"page": "home"})

        # If model query parameters exist, results will be in context
        if "model" in request.query_params:
            model_name = request.query_params["model"]
            parser = context[f"{model_name}_parser"]
            context[f"{model_name}_list"] = await parser.parse_and_execute()

        return await self.templates.render_template(
            request, "index.html", context=context
        )
```
