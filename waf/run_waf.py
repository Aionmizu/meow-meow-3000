from __future__ import annotations

from .config import settings
from .proxy import create_app


def main() -> None:
    app = create_app()
    # Use Flask built-in server for demo; for prod, use gunicorn/uvicorn with ASGI/WSGI adapter
    app.run(host=settings.host, port=settings.port, debug=False)


if __name__ == "__main__":
    main()
