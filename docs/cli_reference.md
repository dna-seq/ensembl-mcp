# CLI Reference

The `ensembl-mcp` CLI provides `serve`, `examples`, and `agent` commands via
Typer. All examples below work with both `uvx --from ensembl-mcp ensembl-mcp`
(PyPI) and `uv run ensembl-mcp` (from source).

## Serve

```bash
# stdio (default) - for Claude Desktop, CLI clients, etc.
ensembl-mcp serve

# streamable HTTP - endpoint at http://<host>:<port>/mcp
ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
```

## Live Examples

```bash
# API version
ensembl-mcp examples version

# Gene lookup
ensembl-mcp examples gene BRCA2

# Variant annotation
ensembl-mcp examples variant rs699

# Resolve rsIDs to coordinates
ensembl-mcp examples resolve-rsids rs699 rs28934578

# Resolve coordinates to variants
ensembl-mcp examples resolve-coordinates 1:230710048 17:7675088

# Available population panels
ensembl-mcp examples populations

# Compara homologies
ensembl-mcp examples homologies ENSG00000139618

# Release metadata
ensembl-mcp examples releases

# Genome search
ensembl-mcp examples genome --scientific-name "Homo sapiens"

# Region overlap
ensembl-mcp examples overlap 13 32315086 32400268

# Bulk gene lookup
ensembl-mcp examples bulk BRCA2 TP53 EGFR

# Refget sequence (subsequence)
ensembl-mcp examples sequence 6aef897c3d6ff0c78aff06ac189178dd --start 0 --end 20

# Refget sequence to file
ensembl-mcp examples sequence 6aef897c3d6ff0c78aff06ac189178dd --start 0 --end 20 --output-name refget_sequence.txt

# Sequence metadata
ensembl-mcp examples sequence-metadata 6aef897c3d6ff0c78aff06ac189178dd

# Raw GraphQL query
ensembl-mcp examples raw '{ version { api { major minor patch } } }'

# Raw GraphQL to file
ensembl-mcp examples raw '{ version { api { major minor patch } } }' --output-name version.json
```

## Natural-Language Agent

Requires dev dependencies and an OpenRouter API key:

```bash
uv sync --dev
# Set in .env: ENSEMBL_MCP_AGENT_API_KEY=<your-key>
```

```bash
# Gene lookups
ensembl-mcp agent "Which human chromosome contains BRCA2?"
ensembl-mcp agent "Find the Ensembl stable id for TP53 in human."
ensembl-mcp agent "Which genes overlap human chromosome 13:32315086-32400268?"

# Variant resolution
ensembl-mcp agent "What are the coordinates and alleles for rs55960271?"
ensembl-mcp agent "Resolve rs587777516 to its GRCh38 coordinates."

# Variant annotation
ensembl-mcp agent "Tell me about variant rs55960271. What gene is it in and what diseases are associated?"

# Batch resolution
ensembl-mcp agent "Resolve rs55960271, rs587777516, rs1063192 to their chromosomes."

# Protein products
ensembl-mcp agent "ENSP00000369497.3 is an Ensembl product stable id. What product type is it, and what is its length?"
```

Use `--model` to override the configured model for one run:

```bash
ensembl-mcp agent --model google/gemini-2.5-flash "Which human chromosome contains BRCA2?"
```
