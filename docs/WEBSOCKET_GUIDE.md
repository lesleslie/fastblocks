# Fastblocks WebSocket Server Guide

## Overview

The Fastblocks WebSocket server provides real-time UI updates, component rendering events, and state synchronization for Fastblocks applications. It enables live preview updates, collaborative editing, and instant state propagation across connected clients.

## Features

- **Component-level subscriptions**: Subscribe to specific component updates
- **Page-level broadcasts**: Broadcast updates to all components on a page
- **Global events**: Application-wide notifications
- **JWT authentication**: Secure connections with optional JWT auth
- **TLS/WSS support**: Secure WebSocket connections
- **Prometheus metrics**: Optional metrics collection
- **Graceful shutdown**: Clean connection handling
- **Message rate limiting**: Configurable rate limits per connection

## Installation

```bash
# Install dependencies
pip install websockets

# Install with extra dependencies
pip install "fastblocks[websocket]"
```

## Quick Start

### Basic Server

```python
import asyncio
from fastblocks.websocket import FastblocksWebSocketServer

async def main():
    # Create server
    server = FastblocksWebSocketServer(
        host="127.0.0.1",
        port=8684
    )

    # Start server
    await server.start()

    # Keep server running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await server.stop()

asyncio.run(main())
```

### With TLS

```python
server = FastblocksWebSocketServer(
    host="0.0.0.0",
    port=8684,
    tls_enabled=True,
    auto_cert=True  # Auto-generate self-signed cert
)

await server.start()
```

### With JWT Authentication

```python
from mcp_common.websocket import WebSocketAuthenticator

# Create authenticator
authenticator = WebSocketAuthenticator(
    secret="your-jwt-secret",
    algorithm="HS256"
)

# Create server with auth
server = FastblocksWebSocketServer(
    port=8684,
    authenticator=authenticator,
    require_auth=True
)

await server.start()
```

## Channels

The WebSocket server uses a room-based channel system:

- `component:{component_id}` - Component-specific updates
- `page:{page_id}` - Page-level broadcasts
- `global` - Application-wide events

### Channel Examples

```python
# Subscribe to navbar component updates
"component:navbar"

# Subscribe to home page updates
"page:home"

# Subscribe to all application events
"global"
```

## Broadcast Methods

### broadcast_ui_updated()

Broadcast UI structure changes to page subscribers.

**Use when**: Component added/removed, layout changes

```python
await server.broadcast_ui_updated(
    page_id="home",
    changes={
        "action": "component_added",
        "component_id": "navbar",
        "position": "top"
    }
)
```

**Event Data**:
```json
{
  "event": "fastblocks.ui_updated",
  "data": {
    "page_id": "home",
    "changes": {...},
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### broadcast_component_rendered()

Broadcast component render event with HTML content.

**Use when**: Component re-renders with new content

```python
await server.broadcast_component_rendered(
    component_id="navbar",
    page_id="home",
    html='<nav class="navbar">...</nav>',
    state={"active": "home"},
    metadata={"render_time": 0.05}
)
```

**Event Data**:
```json
{
  "event": "fastblocks.component_rendered",
  "data": {
    "component_id": "navbar",
    "page_id": "home",
    "html": "<nav>...</nav>",
    "state": {"active": "home"},
    "metadata": {"render_time": 0.05},
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### broadcast_state_changed()

Broadcast state change without full re-render.

**Use when**: Component state updates independently

```python
await server.broadcast_state_changed(
    component_id="counter",
    state={"count": 42, "last_updated": "2024-01-01T00:00:00Z"},
    page_id="home"  # Optional
)
```

**Event Data**:
```json
{
  "event": "fastblocks.state_changed",
  "data": {
    "component_id": "counter",
    "state": {"count": 42},
    "page_id": "home",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

### broadcast_page_loaded()

Broadcast page load event.

```python
await server.broadcast_page_loaded(
    page_id="home",
    url="/home",
    title="Home Page"
)
```

### broadcast_error()

Broadcast error event to subscribers.

```python
await server.broadcast_error(
    error_message="Component failed to render",
    component_id="navbar",
    error_code="RENDER_FAILED"
)
```

## Client Usage

### Basic Connection

```python
import asyncio
import websockets
import json

async def connect_to_fastblocks():
    uri = "ws://127.0.0.1:8684"

    async with websockets.connect(uri) as websocket:
        # Subscribe to component updates
        subscribe_msg = {
            "type": "subscribe",
            "event": "subscribe",
            "data": {"component_id": "navbar"}
        }
        await websocket.send(json.dumps(subscribe_msg))

        # Listen for updates
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect_to_fastblocks())
```

### With Authentication

```python
import asyncio
import websockets
import json

async def connect_with_auth():
    uri = "ws://127.0.0.1:8684"
    token = "your-jwt-token"

    async with websockets.connect(uri) as websocket:
        # Send authentication first
        auth_msg = {
            "type": "request",
            "event": "auth",
            "data": {"token": token}
        }
        await websocket.send(json.dumps(auth_msg))

        # Wait for auth response
        response = await websocket.recv()
        response_data = json.loads(response)

        if response_data.get("status") != "authenticated":
            print("Authentication failed")
            return

        # Now subscribe to updates
        subscribe_msg = {
            "type": "subscribe",
            "data": {"component_id": "navbar"}
        }
        await websocket.send(json.dumps(subscribe_msg))

        # Listen for updates
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect_with_auth())
```

### TLS/WSS Connection

```python
import asyncio
import websockets
import ssl

async def connect_secure():
    uri = "wss://localhost:8684"

    # Create SSL context (for self-signed certs)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        # Connected to secure WebSocket
        async for message in websocket:
            print(f"Received: {message}")

asyncio.run(connect_secure())
```

## MCP Tools Integration

The Fastblocks WebSocket server provides MCP tools for server management:

```python
from fastblocks.mcp.websocket_tools import (
    start_websocket_server,
    stop_websocket_server,
    get_websocket_status,
    broadcast_ui_update,
    broadcast_component_render,
    broadcast_state_change,
)

# Start server
result = await start_websocket_server(
    host="127.0.0.1",
    port=8684,
    tls_enabled=True
)

# Get status
status = await get_websocket_status()

# Broadcast updates
await broadcast_component_render(
    component_id="navbar",
    page_id="home",
    html="<nav>...</nav>",
    state={"active": "home"}
)

# Stop server
await stop_websocket_server()
```

## Testing

```bash
# Run WebSocket server tests
pytest tests/test_websocket_server.py -v

# Run specific test
pytest tests/test_websocket_server.py::TestFastblocksWebSocketServer::test_initialization -v

# Run with coverage
pytest --cov=fastblocks.websocket --cov-report=html tests/test_websocket_server.py
```

## Configuration

### Server Options

| Option | Type | Default | Description |
|--------|------|----------|-------------|
| `host` | str | "127.0.0.1" | Server host address |
| `port` | int | 8684 | WebSocket port |
| `max_connections` | int | 100 | Maximum concurrent connections |
| `message_rate_limit` | int | 100 | Messages per second per connection |
| `authenticator` | WebSocketAuthenticator | None | JWT authenticator instance |
| `require_auth` | bool | False | Require JWT authentication |
| `tls_enabled` | bool | False | Enable TLS |
| `auto_cert` | bool | False | Auto-generate certificate |
| `cert_file` | str | None | Path to TLS certificate |
| `key_file` | str | None | Path to TLS private key |
| `enable_metrics` | bool | False | Enable Prometheus metrics |
| `metrics_port` | int | 9094 | Prometheus metrics port |

### Environment Variables

```bash
# WebSocket configuration
export FASTBLOCKS_WS_HOST="0.0.0.0"
export FASTBLOCKS_WS_PORT="8684"
export FASTBLOCKS_WS_TLS_ENABLED="true"

# Authentication
export FASTBLOCKS_WS_JWT_SECRET="your-secret"
export FASTBLOCKS_WS_AUTH_REQUIRED="true"

# Metrics
export FASTBLOCKS_WS_METRICS_ENABLED="true"
export FASTBLOCKS_WS_METRICS_PORT="9094"
```

## Message Protocol

All WebSocket messages follow the standard protocol:

```json
{
  "id": "unique-message-id",
  "correlation_id": "request-response-id",
  "type": "event|request|response|error",
  "event": "event.name",
  "data": {},
  "timestamp": "2024-01-01T00:00:00Z",
  "room": "channel:name"
}
```

### Message Types

- `request`: Client request expecting response
- `response`: Server response to request
- `event`: Server broadcast event
- `error`: Error message
- `subscribe`: Subscribe to channel
- `unsubscribe`: Unsubscribe from channel

## Error Handling

The server provides comprehensive error handling:

```python
try:
    await server.broadcast_component_rendered(
        component_id="navbar",
        page_id="home",
        html="<nav>...</nav>"
    )
except Exception as e:
    # Broadcast errors are caught and logged
    # Method returns False on failure
    print(f"Broadcast failed: {e}")
```

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_CHANNEL` | Invalid channel specified |
| `SUBSCRIBE_ERROR` | Subscription failed |
| `UNSUBSCRIBE_ERROR` | Unsubscription failed |
| `UNKNOWN_REQUEST` | Unknown request type |
| `REQUEST_ERROR` | Request processing failed |
| `AUTH_FAILED` | Authentication failed |
| `AUTH_REQUIRED` | Authentication required |

## Production Deployment

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expose WebSocket port
EXPOSE 8684

# Expose metrics port
EXPOSE 9094

CMD ["python", "-m", "fastblocks", "websocket", "start"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  fastblocks-ws:
    image: fastblocks:latest
    ports:
      - "8684:8684"   # WebSocket
      - "9094:9094"   # Metrics
    environment:
      - FASTBLOCKS_WS_HOST=0.0.0.0
      - FASTBLOCKS_WS_PORT=8684
      - FASTBLOCKS_WS_TLS_ENABLED=true
      - FASTBLOCKS_WS_CERT_FILE=/certs/cert.pem
      - FASTBLOCKS_WS_KEY_FILE=/certs/key.pem
    volumes:
      - ./certs:/certs:ro
    restart: unless-stopped
```

### Nginx Reverse Proxy

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 443 ssl http2;
    server_name ws.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /ws {
        proxy_pass http://fastblocks-ws:8684;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

## Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl -I http://127.0.0.1:8684

# Check port availability
netstat -an | grep 8684
```

### TLS Errors

```bash
# Verify certificate
openssl s_client -connect localhost:8684 -showcerts

# Check certificate validity
openssl x509 -in cert.pem -text -noout
```

### Performance Issues

```bash
# Check connection count
curl http://127.0.0.1:8684/metrics

# Monitor with Prometheus
curl http://127.0.0.1:9094/metrics
```

## Examples

See `examples/websocket_client_examples.py` for complete client examples:

- Basic UI updates
- Component rendering
- Multi-channel subscriptions
- Request/response patterns

## Related Documentation

- [mcp-common WebSocket Protocol](https://github.com/your-org/mcp-common/blob/main/docs/WEBSOCKET_PROTOCOL.md)
- [Mahavishnu WebSocket Integration](https://github.com/your-org/mahavishnu/blob/main/docs/WEBSOCKET_INTEGRATION.md)
- [Fastblocks Architecture](./ARCHITECTURE.md)

## License

MIT License - see LICENSE file for details
