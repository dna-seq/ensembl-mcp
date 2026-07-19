"""Build a minimal deterministic Claude plugin ZIP archive."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import typer

_SKIP_DIRS = {
    "__pycache__",
    ".venv",
    ".git",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
}

PLUGIN_FILES = [
    Path(".claude-plugin/plugin.json"),
    Path(".mcp.json"),
    Path("README.md"),
    Path("LICENSE"),
]
PLUGIN_DIRECTORIES = [Path(".claude/skills")]


def _zip_paths(source_dir: Path, files: list[Path], dirs: list[Path]) -> list[Path]:
    """Collect allowlisted files and directory trees."""
    missing = [path for path in files if not (source_dir / path).is_file()]
    missing.extend(path for path in dirs if not (source_dir / path).is_dir())
    if missing:
        names = ", ".join(path.as_posix() for path in missing)
        raise FileNotFoundError(f"Missing required paths: {names}")

    result = list(files)
    for directory in dirs:
        result.extend(
            path.relative_to(source_dir)
            for path in (source_dir / directory).rglob("*")
            if path.is_file() and not (_SKIP_DIRS & set(path.parts))
        )
    return sorted(set(result), key=lambda path: path.as_posix())


def build_plugin_archive(source_dir: Path, output: Path | None = None) -> Path:
    """Package only the metadata needed by the Claude plugin."""
    source_dir = source_dir.resolve()
    manifest = json.loads(
        (source_dir / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    version = manifest["version"]
    destination = (
        output or source_dir / "dist" / f"ensembl-claude-plugin-{version}.zip"
    ).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    paths = _zip_paths(source_dir, PLUGIN_FILES, PLUGIN_DIRECTORIES)

    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            info = ZipInfo(path.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                (source_dir / path).read_bytes(),
                compresslevel=9,
            )
    return destination


app = typer.Typer(add_completion=False, help="Package ensembl-mcp for distribution.")


@app.callback()
def package() -> None:
    """Build distribution archives."""


@app.command()
def plugin(
    source_dir: Annotated[
        Path,
        typer.Option("--source-dir", help="Repository root."),
    ] = Path("."),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output ZIP path."),
    ] = None,
) -> None:
    """Build the Claude plugin ZIP."""
    archive = build_plugin_archive(source_dir, output)
    typer.echo(f"Built {archive} ({archive.stat().st_size:,} bytes)")


def cli() -> None:
    """Console-script entry point."""
    app()
