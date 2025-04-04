import pytest
from acb.config import Config
from anyio import Path as AsyncPath
from starlette.applications import Starlette
from starlette.testclient import TestClient
from fastblocks.adapters.routes import default


@pytest.fixture
def config() -> Config:
    config = Config()
    config.storage.local_fs = True
    return config


@pytest.fixture
def routes(config: Config) -> default.Routes:
    routes = default.Routes()
    return routes


@pytest.fixture
def app(routes: default.Routes) -> Starlette:
    app = Starlette(routes=routes.routes)  # type: ignore
    return app


@pytest.mark.anyio
async def test_index_get(app: Starlette, config: Config, tmp_path: AsyncPath) -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "hx-request" in response.headers["vary"]
    assert "home" in response.text
    response = client.get("/about")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "hx-request" in response.headers["vary"]
    assert "about" in response.text
    response = client.get("/notfound")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_index_get_htmx(
    app: Starlette, config: Config, tmp_path: AsyncPath
) -> None:
    client = TestClient(app)
    response = client.get("/", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "hx-push-url" in response.headers
    assert "/" == response.headers["hx-push-url"]
    assert "home" in response.text
    response = client.get("/about", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "hx-push-url" in response.headers
    assert "/about" == response.headers["hx-push-url"]
    assert "about" in response.text


@pytest.mark.anyio
async def test_block_get(app: Starlette, config: Config, tmp_path: AsyncPath) -> None:
    response = TestClient(app).get("/block/test")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_favicon(app: Starlette, config: Config, tmp_path: AsyncPath) -> None:
    response = TestClient(app).get("/favicon.ico")
    assert response.status_code == 200
    assert response.text == ""


@pytest.mark.anyio
async def test_robots(app: Starlette, config: Config, tmp_path: AsyncPath) -> None:
    response = TestClient(app).get("/robots.txt")
    assert response.status_code == 200
    assert "User-agent: *" in response.text
    assert "Disallow: /dashboard/" in response.text
    assert "Disallow: /blocks/" in response.text


@pytest.mark.anyio
async def test_gather_routes(
    routes: default.Routes, config: Config, tmp_path: AsyncPath
) -> None:
    test_routes_path = tmp_path / "_routes.py"
    test_route_content = (
        "from starlette.responses import PlainTextResponse"
        "from starlette.routing import Route"
        ""
        "async def test_endpoint(request):"
        "    return PlainTextResponse('test')"
        ""
        "routes = ["
        "    Route('/test', test_endpoint)"
        "]"
    )
    await test_routes_path.write_text(test_route_content)
    await routes.gather_routes(test_routes_path)
    assert len(routes.routes) > 5
    app = Starlette(routes=routes.routes)  # type: ignore
    response = TestClient(app).get("/test")
    assert response.status_code == 200
    assert response.text == "test"


@pytest.mark.anyio
async def test_static_files(
    app: Starlette, config: Config, tmp_path: AsyncPath
) -> None:
    config.storage.local_path = tmp_path
    config.storage.local_fs = True
    test_file_path = tmp_path / "media" / "test.txt"
    await test_file_path.parent.mkdir(parents=True, exist_ok=True)
    await test_file_path.write_text("test")
    client = TestClient(app)
    response = client.get("/media/test.txt")
    assert response.status_code == 200
    assert response.text == "test"
    response = client.get("/media/notfound.txt")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_init(
    routes: default.Routes, config: Config, tmp_path: AsyncPath
) -> None:
    await routes.init()
    assert len(routes.routes) > 5
