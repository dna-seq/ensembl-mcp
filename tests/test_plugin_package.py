import json
from pathlib import Path
from zipfile import ZipFile

from ensembl_mcp.plugin_package import PLUGIN_FILES, build_plugin_archive


def test_plugin_archive_contains_only_runtime_metadata(tmp_path: Path) -> None:
    source_dir = Path(__file__).parents[1]
    archive_path = build_plugin_archive(source_dir, tmp_path / "ensembl-plugin.zip")

    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert {path.as_posix() for path in PLUGIN_FILES} <= names
    assert ".claude/skills/ensembl-variant-lookup/SKILL.md" in names
    assert not any(
        name.startswith(("src/", "tests/", ".git/", ".venv/")) for name in names
    )
    assert archive_path.stat().st_size < 1_000_000


def test_plugin_archive_is_deterministic(tmp_path: Path) -> None:
    source_dir = Path(__file__).parents[1]
    first = build_plugin_archive(source_dir, tmp_path / "first.zip")
    second = build_plugin_archive(source_dir, tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()


def test_claude_plugin_declares_runtime_components() -> None:
    source_dir = Path(__file__).parents[1]
    manifest = json.loads(
        (source_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["skills"] == "./.claude/skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert (source_dir / manifest["skills"].removeprefix("./")).is_dir()
    assert (source_dir / manifest["mcpServers"].removeprefix("./")).is_file()


def test_codex_plugin_points_to_reusable_components() -> None:
    source_dir = Path(__file__).parents[1]
    manifest = json.loads(
        (source_dir / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    mcp_config = json.loads(
        (source_dir / manifest["mcpServers"].removeprefix("./")).read_text(encoding="utf-8")
    )

    assert (source_dir / manifest["skills"].removeprefix("./")).is_dir()
    assert mcp_config["mcp_servers"]["ensembl"]["args"] == [
        "ensembl-mcp@0.3.0",
        "serve",
    ]
