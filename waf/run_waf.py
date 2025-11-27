from __future__ import annotations

from .config import settings
from .proxy import create_app_with_error_handler


def main() -> None:
    # Use the variant with global error handler to guarantee logging on any failure
    app = create_app_with_error_handler()
    # Use Flask built-in server for demo; for prod, use gunicorn/uvicorn with ASGI/WSGI adapter
    app.run(host=settings.host, port=settings.port, debug=False)


if __name__ == "__main__":
    main()
