from ensembl_mcp.cli import app
from ensembl_mcp.server import create_server


def main() -> None:
    """Console-script entrypoint that launches the Typer CLI."""
    app()


__all__ = ["app", "create_server", "main"]
