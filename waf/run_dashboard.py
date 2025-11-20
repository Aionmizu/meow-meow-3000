from __future__ import annotations

from .config import settings
from .dashboard_app import create_dashboard_app


def main() -> None:
    app = create_dashboard_app()
    app.run(host=settings.dashboard_host, port=settings.dashboard_port, debug=False)


if __name__ == "__main__":
    main()
