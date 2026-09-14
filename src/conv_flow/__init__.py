import uvicorn

from conv_flow.config import settings
from conv_flow.main import app


def main() -> None:
    """Main entry point for CLI."""
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
