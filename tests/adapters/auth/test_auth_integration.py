import asyncio
from typing import Any

import pytest
from pydantic import SecretStr
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from fastblocks.adapters.auth.basic import Auth


@pytest.mark.integration
class TestBasicAuthIntegration:
    def test_basic_auth_with_session_middleware(self) -> None:
        auth = Auth(
            secret_key=SecretStr("secret"),
            users={"alice": "wonderland"},
        )

        async def protected(request: Any) -> Response:
            if not await auth.authenticate(request):
                return Response(
                    "Unauthorized",
                    status_code=401,
                    headers={"WWW-Authenticate": "Basic"},
                )
            return Response("OK", status_code=200)

        app = Starlette(routes=[Route("/protected", protected)])
        # Attach auth session middleware
        asyncio.run(auth.init())
        for middleware in auth.middlewares:
            app.add_middleware(middleware.cls, **middleware.kwargs)

        client = TestClient(app)
        credentials = "Basic YWxpY2U6d29uZGVybGFuZA=="  # alice:wonderland
        response = client.get("/protected", headers={"Authorization": credentials})

        assert response.status_code == 200
