from __future__ import annotations

import os

from app import create_app

app = create_app()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=_bool_env("FLASK_DEBUG", bool(app.config.get("DEBUG", False))),
        use_reloader=_bool_env("FLASK_USE_RELOADER", False),
    )
