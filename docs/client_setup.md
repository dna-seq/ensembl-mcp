# Client Setup

Detailed configuration for connecting ensembl-mcp to various LLM clients and agents.

## Method A: Using `uvx` (Recommended)

Since the package is published on PyPI, you can configure your client to run it
directly without cloning the repository.

### Claude Desktop and Cowork

Add the following to your `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

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

Claude Cowork reuses the local MCP servers configured in Claude Desktop. Restart
Claude Desktop after saving, then open a Cowork session to use the Ensembl tools.

### Cursor IDE

1. Open **Cursor Settings** (gear icon or `Ctrl+,` / `Cmd+,`).
2. Navigate to **Features** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. Fill in:
   - **Name**: `ensembl`
   - **Type**: `command`
   - **Command**: `uvx ensembl-mcp serve`
5. Click **Save**.

### Claude Code

```bash
claude mcp add ensembl uvx ensembl-mcp serve
```

### Codex CLI, ChatGPT Desktop, and the Codex IDE extension

Install the native Codex plugin to get both the Ensembl MCP server and the
bundled genomics skills:

```bash
codex plugin marketplace add dna-seq/ensembl-mcp
```

Open Codex and run `/plugins`, choose **DNA-Seq Plugins**, then install
**Ensembl: Genes, Variants, and Sequences**.

For a tools-only setup, Codex clients also share direct MCP configuration. Add
the server once from a terminal:

```bash
codex mcp add ensembl -- uvx ensembl-mcp serve
```

Start a new Codex session, then run `/mcp` to confirm it is connected. To add
that server manually, place this in `~/.codex/config.toml` (or
`.codex/config.toml` for a trusted project):

```toml
[mcp_servers.ensembl]
command = "uvx"
args = ["ensembl-mcp", "serve"]
```

### Google Antigravity

In the Agent panel, select **⋯** → **MCP Servers** → **Manage MCP Servers** →
**View raw config**, then add this server to the `mcpServers` object:

```json
{
  "ensembl": {
    "command": "uvx",
    "args": ["ensembl-mcp", "serve"]
  }
}
```

Save the configuration and use the MCP Servers panel to verify that Ensembl is
connected. Antigravity normally stores its shared configuration at
`~/.gemini/config/mcp_config.json`. If it cannot resolve `uvx`, use the
absolute executable path printed by `which uvx` as the `command` value.

### Cline / Roo Code (VS Code Extensions)

Edit your local MCP settings file (typically accessible via the extension's MCP
settings tab):

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

## Method B: Running from Source (For development)

If you prefer running from your local clone, configure your client as follows.

### Claude Desktop

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

> **Note:** Replace `/absolute/path/to/ensembl-mcp` with the actual path where
> you cloned this repository.

### Cursor IDE

1. Open **Cursor Settings**.
2. Navigate to **Features** -> **MCP**.
3. Click **+ Add New MCP Server**.
4. **Command**: `uv --directory "/absolute/path/to/ensembl-mcp" run ensembl-mcp serve`
5. Click **Save**.

### Claude Code

```bash
claude mcp add ensembl uv --directory "/absolute/path/to/ensembl-mcp" run ensembl-mcp serve
```

### Cline / Roo Code

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

## Claude plugin

The repository is a Claude plugin directory during development:

```bash
claude --plugin-dir .
```

Build the deterministic metadata-only plugin archive with:

```bash
uv run pack plugin
```

The ZIP contains the plugin manifest, pinned `uvx` MCP configuration, variant
lookup skill, README, and license. The server itself remains distributed through
PyPI and is launched as `uvx ensembl-mcp@0.3.0 serve`.

## Environment Variables

Pass environment variables through your client's configuration:

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uvx",
      "args": ["ensembl-mcp", "serve"],
      "env": {
        "ENSEMBL_MCP_REQUEST_TIMEOUT": "120"
      }
    }
  }
}
```

See [configuration.md](configuration.md) for all available variables.
