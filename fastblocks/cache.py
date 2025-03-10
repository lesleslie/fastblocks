import typing as t

from acb.actions.hash import hash
from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends

Cache, Logger = import_adapter()  # type: ignore


@depends.inject
async def get_cache_key(
    func: t.Any, args: t.Any, kwargs: t.Any, config: Config = depends()
) -> str:
    cache_key = await hash.md5(  # noqa: S324
        f"{func.__module__}:{func.__name__}:{args}:{kwargs}"
    )
    return f"{config.app.name}:func:{cache_key}"


@depends.inject
async def get_from_cache(
    key: str,
    cache: Cache = depends(),
    logger: Logger = depends(),
) -> bytes | None:
    try:
        return await cache.get(key)
    except Exception as e:
        logger.exception(f"Couldn't retrieve {key}, {e}")
    return None


@depends.inject
async def set_in_cache(
    key: str,
    value: bytes,
    ttl: t.Optional[int] = None,
    cache: Cache = depends(),
    logger: Logger = depends(),
) -> None:
    try:
        await cache.set(key, value, ttl=ttl)
    except Exception as e:
        logger.exception(f"Couldn't set {value} in key {key}, {e}")


def cached(func: t.Any, ttl: t.Optional[int] = None):
    async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        key = await get_cache_key(func, args, kwargs)
        value = await get_from_cache(key)
        if value is not None:
            return value
        result = await func(*args, **kwargs)
        await set_in_cache(key, result, ttl=ttl)
        return result

    return wrapper
