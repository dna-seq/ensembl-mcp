# Configuration

Set via `ENSEMBL_MCP_*` environment variables or a `.env` file. The project
loads `.env` explicitly with `load_dotenv()` before pydantic-settings reads the
configuration. Use `.env.template` as the list of supported local values.

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `ENSEMBL_MCP_ENDPOINT` | `https://beta.ensembl.org/data/graphql/core` | GraphQL endpoint. |
| `ENSEMBL_MCP_REFGET_ENDPOINT` | `https://beta.ensembl.org/data/refget` | Refget endpoint for sequence retrieval. |
| `ENSEMBL_MCP_VARIATION_ENDPOINT` | `https://beta.ensembl.org/api/graphql/variation` | Short-variant GraphQL endpoint. |
| `ENSEMBL_MCP_COMPARA_ENDPOINT` | `https://beta.ensembl.org/api/graphql/compara` | Homology GraphQL endpoint. |
| `ENSEMBL_MCP_METADATA_ENDPOINT` | `https://beta.ensembl.org/api/metadata` | Beta metadata REST base URL. |
| `ENSEMBL_MCP_REST_ENDPOINT` | `https://rest.ensembl.org` | Legacy REST base used for bare-rsID resolution. |
| `ENSEMBL_MCP_REQUEST_TIMEOUT` | `60` | HTTP timeout (seconds). |
| `ENSEMBL_MCP_HUMAN_GENOME_ID` | `a7335667-93e7-11ec-a39d-005056b38ce3` | Default genome id. |
| `ENSEMBL_MCP_OUTPUT_DIR` | `.ensembl_mcp_outputs` | Directory for file-output tools. |
| `ENSEMBL_MCP_AGENT_API_KEY` | unset | OpenRouter API key for the optional Agno agent. |
| `ENSEMBL_MCP_AGENT_MODEL_ID` | `z-ai/glm-5.2` | Model id for the Agno agent (any OpenRouter model). |
| `ENSEMBL_MCP_AGENT_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible base URL. |
| `ENSEMBL_MCP_AGENT_TIMEOUT` | `120` | LLM call timeout (seconds). |

FastMCP background-task backend is configured via `FASTMCP_DOCKET_URL`
(`memory://` by default; `redis://...` for multi-worker scaling).
