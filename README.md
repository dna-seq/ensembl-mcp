# ensembl-mcp

An [MCP](https://modelcontextprotocol.io) server for the
[Ensembl beta GraphQL API](https://beta.ensembl.org/data/graphql/core), built on
[FastMCP](https://gofastmcp.com).

- Runs over **stdio** and **streamable HTTP**.
- Every data tool is **background-task capable** (MCP SEP-1686 via FastMCP
  `TaskConfig`, default in-process `memory://` backend - no Redis/Docker needed).
- Ships with a **Typer CLI** to serve the server and run live examples.
- Includes an optional **Agno natural-language agent** for advanced integration
  tests and manual query resolution.

## Install

### 1. Via PyPI (Recommended)

You can run the MCP server directly without cloning the repository using `uvx`:

```bash
uvx ensembl-mcp serve
```

### 2. From Source (For development)

Clone this repository locally and run:

```bash
uv sync
```

Requires Python 3.14+.

For agentic tests and the natural-language CLI entrypoint, install dev
dependencies:

```bash
uv sync --dev
```

## Connecting to LLM Clients & Agents

To use this MCP server with your favorite AI tools (like Claude Desktop, Cursor, Claude Code, Cline, etc.), you'll configure them to run the server over **stdio**.

### Method A: Using `uvx` (Recommended)

Since the package is published on PyPI, you can configure your client to run it directly without cloning the repository:

#### 1. Claude Desktop

Add the following to your `claude_desktop_config.json`:

*   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
*   **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uvx",
      "args": [
        "ensembl-mcp",
        "serve"
      ]
    }
  }
}
```

#### 2. Cursor IDE

Add a new MCP server in the settings:
1. Open **Cursor Settings** (gear icon or `Ctrl+,` / `Cmd+,`).
2. Navigate to **Features** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. Fill in the fields:
   * **Name**: `ensembl`
   * **Type**: `command`
   * **Command**: `uvx ensembl-mcp serve`
5. Click **Save**.

#### 3. Claude Code

For the Claude CLI developer agent (`claudecode`), you can add this server by running:

```bash
claude mcp add ensembl uvx ensembl-mcp serve
```

#### 4. Cline / Roo Code (VS Code Extensions)

If you use VS Code extensions like **Cline** or **Roo Code**, edit your local MCP settings file (typically accessible via the extension's MCP settings tab):

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uvx",
      "args": [
        "ensembl-mcp",
        "serve"
      ]
    }
  }
}
```

---

### Method B: Running from Source (For development)

If you prefer running from your local clone, configure your client as follows:

#### 1. Claude Desktop

Add the following to your `claude_desktop_config.json`:

*   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
*   **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/ensembl-mcp",
        "run",
        "ensembl-mcp",
        "serve"
      ]
    }
  }
}
```

> **Note:** Replace `/absolute/path/to/ensembl-mcp` with the actual path where you cloned this repository.

#### 2. Cursor IDE

You can add this MCP server directly in the Cursor Settings UI:

1. Open **Cursor Settings** (gear icon or `Ctrl+,` / `Cmd+,`).
2. Navigate to **Features** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. Fill in the fields:
   *   **Name**: `ensembl`
   *   **Type**: `command`
   *   **Command**:
       ```bash
       uv --directory "/absolute/path/to/ensembl-mcp" run ensembl-mcp serve
       ```
5. Click **Save**.

#### 3. Claude Code

For the Claude CLI developer agent (`claudecode`), you can add this server by running:

```bash
claude mcp add ensembl uv --directory "/absolute/path/to/ensembl-mcp" run ensembl-mcp serve
```

#### 4. Cline / Roo Code (VS Code Extensions)

If you use VS Code extensions like **Cline** or **Roo Code**, edit your local MCP settings file:

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/ensembl-mcp",
        "run",
        "ensembl-mcp",
        "serve"
      ]
    }
  }
}
```

---

### Customizing Configuration (Environment Variables)

If you need to configure or customize behavior (such as setting the default genome or API endpoint), you can pass environment variables in your client's configuration.

For example, in **Claude Desktop** or **Cline**:

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uvx",
      "args": [
        "ensembl-mcp",
        "serve"
      ],
      "env": {
        "ENSEMBL_MCP_REQUEST_TIMEOUT": "120"
      }
    }
  }
}
```

See [Configuration](#configuration) below for all available environment variables.

## Run the server

### Via PyPI (Recommended)

```bash
# stdio (default) - for Claude Desktop, CLI clients, etc.
uvx ensembl-mcp serve

# streamable HTTP - endpoint at http://<host>:<port>/mcp
uvx ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
```

### From Source (For development)

```bash
# stdio (default) - for Claude Desktop, CLI clients, etc.
uv run ensembl-mcp serve

# streamable HTTP - endpoint at http://<host>:<port>/mcp
uv run ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
```

## Tools

| Tool | Description |
| --- | --- |
| `get_version` | Ensembl GraphQL API version. |
| `find_genes_by_symbol` | Genes by display symbol (e.g. `BRCA2`). |
| `get_gene_by_id` | Gene by Ensembl stable id. |
| `get_transcript` | Transcript by stable id or symbol. |
| `transcript_search` | Full-text transcript search across genomes. |
| `get_product_by_id` | Protein product by stable id. |
| `get_region` | Region (e.g. chromosome) by name. |
| `overlap_region` | Genes/transcripts overlapping a genomic interval. |
| `find_genomes` | Resolve a species/assembly keyword to genome(s) + `genome_id`. |
| `get_genome` | Genome metadata by `genome_id`. |
| `graphql_query` | Run an arbitrary raw GraphQL query. |
| `bulk_find_genes` | Resolve many symbols at once (background-task showcase, with progress). |

Most lookups accept a `genome_id` (UUID); it defaults to the human reference
`a7335667-93e7-11ec-a39d-005056b38ce3`. Use `find_genomes` for other species.

## CLI examples (live)

### Via PyPI (Recommended)

```bash
uvx --from ensembl-mcp ensembl-mcp examples version
uvx --from ensembl-mcp ensembl-mcp examples gene BRCA2
uvx --from ensembl-mcp ensembl-mcp examples genome --scientific-name "Homo sapiens"
uvx --from ensembl-mcp ensembl-mcp examples overlap 13 32315086 32400268
uvx --from ensembl-mcp ensembl-mcp examples bulk BRCA2 TP53 EGFR
uvx --from ensembl-mcp ensembl-mcp examples raw '{ version { api { major minor patch } } }'
```

### From Source (For development)

```bash
uv run ensembl-mcp examples version
uv run ensembl-mcp examples gene BRCA2
uv run ensembl-mcp examples genome --scientific-name "Homo sapiens"
uv run ensembl-mcp examples overlap 13 32315086 32400268
uv run ensembl-mcp examples bulk BRCA2 TP53 EGFR
uv run ensembl-mcp examples raw '{ version { api { major minor patch } } }'
```

## Natural-Language Agent

The optional Agno agent lets you ask natural-language questions from the CLI.

### Via PyPI (Recommended)

```bash
# Make sure to set GEMINI_API_KEY, GOOGLE_API_KEY, or ENSEMBL_MCP_AGENT_API_KEY in your environment first
uvx --from ensembl-mcp ensembl-mcp agent "your natural-language Ensembl question"
```

### From Source (For development)

Its entrypoint is:

```bash
uv run ensembl-mcp agent "your natural-language Ensembl question"
```

Internally, the agent selects and calls the same live Ensembl operations exposed
as MCP tools, then summarizes the result. Install dev dependencies first because
Agno and model providers are development dependencies:

```bash
uv sync --dev
```

Configure a model key in `.env`. For OpenAI-compatible models:

```bash
ENSEMBL_MCP_AGENT_API_KEY=
ENSEMBL_MCP_AGENT_MODEL_ID=gpt-4o-mini
```

For Gemini models:

```bash
ENSEMBL_MCP_AGENT_MODEL_ID=gemini-flash-latest
GEMINI_API_KEY=
# or GOOGLE_API_KEY=
```

Then ask a question:

#### Via PyPI (Recommended)

```bash
uvx --from ensembl-mcp ensembl-mcp agent "Which human chromosome contains BRCA2?"
uvx --from ensembl-mcp ensembl-mcp agent "Find the Ensembl stable id for TP53 in human."
uvx --from ensembl-mcp ensembl-mcp agent "Which genes overlap human chromosome 13:32315086-32400268?"
```

#### From Source (For development)

```bash
uv run ensembl-mcp agent "Which human chromosome contains BRCA2?"
uv run ensembl-mcp agent "Find the Ensembl stable id for TP53 in human."
uv run ensembl-mcp agent "Which genes overlap human chromosome 13:32315086-32400268?"
```

Use `--model` to override `ENSEMBL_MCP_AGENT_MODEL_ID` for one run:

```bash
# Via PyPI
uvx --from ensembl-mcp ensembl-mcp agent --model gemini-flash-latest "Which human chromosome contains BRCA2?"

# From Source
uv run ensembl-mcp agent --model gemini-flash-latest "Which human chromosome contains BRCA2?"
```

## Configuration

Set via `ENSEMBL_MCP_*` environment variables or a `.env` file. The project
loads `.env` explicitly with `load_dotenv()` before pydantic-settings reads the
configuration. Use `.env.template` as the list of supported local values.

| Variable | Default | Description |
| --- | --- | --- |
| `ENSEMBL_MCP_ENDPOINT` | `https://beta.ensembl.org/data/graphql/core` | GraphQL endpoint. |
| `ENSEMBL_MCP_REQUEST_TIMEOUT` | `60` | HTTP timeout (seconds). |
| `ENSEMBL_MCP_HUMAN_GENOME_ID` | `a7335667-93e7-11ec-a39d-005056b38ce3` | Default genome id. |
| `ENSEMBL_MCP_AGENT_API_KEY` | unset | API key for the optional Agno agent. |
| `ENSEMBL_MCP_AGENT_MODEL_ID` | `gpt-4o-mini` | Model id for the Agno agent. `gemini...` ids use the Gemini adapter. |
| `ENSEMBL_MCP_AGENT_BASE_URL` | unset | Optional OpenAI-compatible base URL. |
| `ENSEMBL_MCP_AGENT_TIMEOUT` | `120` | LLM call timeout (seconds). |
| `GEMINI_API_KEY` | unset | Gemini API key fallback for `gemini...` agent models. |
| `GOOGLE_API_KEY` | unset | Google API key fallback for `gemini...` agent models. |

FastMCP background-task backend is configured via `FASTMCP_DOCKET_URL`
(`memory://` by default; `redis://...` for multi-worker scaling).

## Tests

Integration tests hit the live endpoint and skip gracefully when offline:

```bash
uv run pytest
```

The Agno natural-language integration test also requires
`ENSEMBL_MCP_AGENT_API_KEY`; without it, that test is skipped.

## Scope

The Ensembl beta `data/graphql` gateway currently serves only the core schema
(genes, transcripts, products, regions, genomes). It does **not** provide variant
resolution by rsid or coordinate - that belongs to the separate
`ensembl-hypsipyle` variation service, which is not reachable from this gateway.
Variants are therefore out of scope.
