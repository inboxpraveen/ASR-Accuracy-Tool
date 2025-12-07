from pathlib import Path

from flask import Flask

from asr_tool.config import BASE_DIR, Config, ensure_directories
from asr_tool.routes import bp as api_bp


def create_app() -> Flask:
    """Application factory kept minimal—no Celery/Redis required."""
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "static"),
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config.from_object(Config)

    ensure_directories()

    app.register_blueprint(api_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, threaded=True)

