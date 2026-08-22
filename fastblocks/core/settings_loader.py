"""fastblocks settings loader.

Wraps Oneiric's load_settings with fastblocks defaults: project_name="fastblocks",
default path resolution via Oneiric's XDG-compliant layered lookup.
Returns AppSettings (not raw OneiricSettings) so callers get the
fastblocks schema.

Soft-fallback contract: callers (typically AppSettings() instantiation
sites) should wrap the call in `try/except FileNotFoundError` to
preserve the "defaults-only when no app.yml exists" back-compat
behavior.
"""

from __future__ import annotations

from pathlib import Path

from fastblocks.adapters.app.default import AppSettings

# Re-export so callers can catch the "missing file" case explicitly.
_FILE_NOT_FOUND = FileNotFoundError


def load_fastblocks_settings(
    path: str | Path | None = None,
) -> AppSettings:
    """Load AppSettings from app.yml (or fallback path).

    Wraps Oneiric's load_settings for fastblocks defaults.
    Raises FileNotFoundError if no app.yml exists at any resolved path;
    callers handle the fallback.

    Args:
        path: Optional explicit path. Highest priority. Defaults to
            Oneiric's XDG-compliant layered lookup
            (~/.config/fastblocks/config.yaml → ./app.yml → defaults).

    Returns:
        AppSettings populated from YAML + Oneiric defaults.
    """
    from oneiric.core.config import load_settings  # local import — avoids module-load cycle

    if path is not None and not Path(path).exists():
        raise FileNotFoundError(f"app.yml not found at {path}")
    oneiric = load_settings(path=path, project_name="fastblocks")
    return AppSettings.model_validate(oneiric.model_dump(mode="python"))


__all__ = ["load_fastblocks_settings", "_FILE_NOT_FOUND"]
