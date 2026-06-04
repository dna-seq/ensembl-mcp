# AGENTS.md

Guidance for AI agents and contributors working in this repository. `CLAUDE.md`
is a symlink to this file, so keep everything here.

## What this is

`ensembl-mcp` is a [FastMCP](https://gofastmcp.com) server exposing the
[Ensembl beta GraphQL API](https://beta.ensembl.org/data/graphql/core) as MCP
tools. It runs over both stdio and streamable HTTP, and every data tool is
background-task capable (MCP SEP-1686 via FastMCP `TaskConfig`).

## Layout

- `src/ensembl_mcp/config.py` - `pydantic-settings` config (`ENSEMBL_MCP_*` env / `.env`).
- `src/ensembl_mcp/models.py` - pydantic 2 input models mirroring GraphQL input types.
- `src/ensembl_mcp/client.py` - async `httpx` GraphQL client with eliot logging.
- `src/ensembl_mcp/queries.py` - GraphQL query strings (field selections verified live).
- `src/ensembl_mcp/server.py` - `op_*` data functions (testable) + `create_server()` MCP tools.
- `src/ensembl_mcp/agent.py` - optional Agno natural-language agent over the same `op_*` functions.
- `src/ensembl_mcp/cli.py` - Typer app: `serve` and `examples` commands.
- `tests/` - real integration tests against the live endpoint.

## Conventions

- Use `uv` for everything: `uv sync`, `uv add`, `uv add --dev`, `uv run`.
- Never hardcode the package version in `__init__.py`; it lives in `pyproject.toml`.
- Always use type hints. Use pydantic 2. Use Typer for CLIs.
- No relative imports - import from `ensembl_mcp.*`.
- Load environment from `.env` with `load_dotenv()` before reading settings.
- Prefer eliot `start_action` for logging; avoid excessive try/except inside actions.
- Tests are real integration tests (no mocks); skip gracefully when offline. Avoid
  trivial tests (e.g. asserting a field we defined ourselves exists).
- Agno is a dev dependency. Keep imports isolated so the MCP server can run without
  agent dependencies installed.
- Gemini agent models use `GEMINI_API_KEY` or `GOOGLE_API_KEY` from `.env`; do not
  commit real keys.

## Common commands

```bash
uv sync                                   # install deps
uv run ensembl-mcp serve                  # stdio transport
uv run ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
uv run ensembl-mcp examples gene BRCA2    # live example
uv run ensembl-mcp agent "Which human chromosome contains BRCA2?"
uv run pytest -m integration              # run integration tests
```

## Agent testing

- Configure `ENSEMBL_MCP_AGENT_API_KEY` in `.env` to run Agno tests or the
  `ensembl-mcp agent` command. For `gemini...` models, configure `GEMINI_API_KEY`
  or `GOOGLE_API_KEY` instead.
- The natural-language tests call both the configured LLM and the live Ensembl
  endpoint; skip them when the key is absent rather than mocking the behavior.

## Scope notes

- The Ensembl beta `data/graphql` gateway exposes only the core schema (genes,
  transcripts, products, regions, genomes). It has no variant/rsid/coordinate
  variant resolution - that lives in the separate `ensembl-hypsipyle` variation
  service, which is not currently reachable. Variants are intentionally out of scope.
- Most lookups require a `genome_id` (UUID). The human reference genome_id default is
  `a7335667-93e7-11ec-a39d-005056b38ce3`. Use `find_genomes` to resolve other species.
