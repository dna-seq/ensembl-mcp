# AGENTS.md

Guidance for AI agents and contributors working in this repository. `CLAUDE.md`
is a symlink to this file, so keep everything here.

## What this is

`ensembl-mcp` is a [FastMCP](https://gofastmcp.com) server exposing Ensembl beta
core, variation, compara, metadata, legacy variation REST, and GA4GH Refget APIs
as MCP tools. It runs over both stdio and streamable HTTP, and every data tool is
background-task capable (MCP SEP-1686 via FastMCP `TaskConfig`).

## Layout

- `src/ensembl_mcp/config.py` - `pydantic-settings` config (`ENSEMBL_MCP_*` env / `.env`).
- `src/ensembl_mcp/models.py` - pydantic 2 input models and typed variation
  response contracts published through MCP output schemas.
- `src/ensembl_mcp/client.py` - async `httpx` GraphQL client with eliot logging.
- `src/ensembl_mcp/queries.py` - GraphQL query strings (field selections verified live).
- `src/ensembl_mcp/backend_queries.py` - variation and compara GraphQL selections.
- `src/ensembl_mcp/server.py` - `op_*` data functions (testable) + `create_server()` MCP tools.
  - Core gene/transcript/product lookups with enriched fields (xrefs, MANE, exons, domains).
  - Variant tools: annotation, clinical summary, region scan, recoder, protein sequence bridge.
  - `_build_clinical_summary` distills full variant annotation into filtered compact view.
- `src/ensembl_mcp/agent.py` - optional Agno natural-language agent over the same `op_*` functions.
- `src/ensembl_mcp/cli.py` - Typer app: `serve` and `examples` commands.
- `src/ensembl_mcp/plugin_package.py` - deterministic metadata-only Claude plugin ZIP.
- `.mcp.json` and `.codex.mcp.json` - published-package MCP launch configuration.
- `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` - plugin manifests.
- `.github/workflows/publish.yml` - tag/manual PyPI publishing workflow.
- `tests/test_enriched_tools.py` - integration tests for enriched fields and new tools (Phases 1-3).
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
- The default agent model is `z-ai/glm-5.2` via OpenRouter; do not commit real keys.
- Use `get_sequence_to_file` for large Refget sequences and `graphql_query_to_file`
  for raw GraphQL results that may be large instead of returning them directly
  into an LLM context.

## Common commands

```bash
uv sync                                   # install deps
uv run ensembl-mcp serve                  # stdio transport
uv run ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
uv run ensembl-mcp examples gene BRCA2    # live example
uv run ensembl-mcp examples variant rs699 # live variant example
uv run ensembl-mcp agent "Which human chromosome contains BRCA2?"
uv run pytest -m integration              # run integration tests
uv run pack plugin                        # build thin Claude plugin ZIP
```

## Releasing and publishing

- Keep the version in `pyproject.toml`, both plugin manifests, `.mcp.json`, and
  `.codex.mcp.json` aligned. The MCP configs use `uvx ensembl-mcp@<version> serve`,
  so that exact version must exist on PyPI before installed plugins can start.
- Local PyPI publishing credentials are stored in `.env`. Never print, log, or
  commit them. Load `.env` into the process environment before running `uv publish`;
  accept either `UV_PUBLISH_TOKEN` or `PYPI_TOKEN`.
- `dist/` also contains Claude plugin ZIPs and older releases. Publish the newly
  built wheel and source archive explicitly instead of publishing every file:

```bash
uv build
set -a && source .env && set +a
export UV_PUBLISH_TOKEN="${UV_PUBLISH_TOKEN:-${PYPI_TOKEN:-}}"
uv publish "dist/ensembl_mcp-<version>-py3-none-any.whl" \
  "dist/ensembl_mcp-<version>.tar.gz"
uvx --refresh "ensembl-mcp@<version>" --help
```

- `.github/workflows/publish.yml` publishes on `v*` tags or manual dispatch using
  the repository `PYPI_TOKEN` secret. If that secret is unavailable, use the local
  `.env` credential.

## Agent testing

- Configure `ENSEMBL_MCP_AGENT_API_KEY` in `.env` with an OpenRouter API key to
  run Agno tests or the `ensembl-mcp agent` command.
- The natural-language tests call both the configured LLM and the live Ensembl
  endpoint; skip them when the key is absent rather than mocking the behavior.
- Variant agent tests must verify real nested data, not just that an rsID appears:
  preserve every allele at multiallelic sites, name frequency populations, keep
  predictions at variant/allele/transcript-consequence scope, and treat phenotype
  assertions as sourced associations.

## Variant response contract

- Keep the selected GraphQL fields in `backend_queries.py`, the Pydantic response
  models in `models.py`, MCP tool descriptions, README, and live tests aligned.
- Validate response-model changes against live full and compact payloads for both
  `rs699` (`1:230710048:rs699`) and `rs28934578`
  (`17:7675088:rs28934578`). The beta docs and schema can lag production.
- `VariantAnnotation.prediction_results` is variant-level (VEP, GERP,
  AncestralAllele); `VariantAllele.prediction_results` is allele-level (CADD);
  `MolecularConsequence.prediction_results` is transcript-level (SIFT, SpliceAI,
  and sometimes PolyPhen). Do not flatten these collections.
- Frequencies are meaningful only with `population_name`. Allele count/number can
  be null for inferred reference alleles, phenotype ontology/evidence fields are
  often null or empty, and some alleles have no population records.
- `full=False` omits phenotype assertions and molecular consequences. Keep those
  model fields optional so compact payloads validate without fabricating data.
- Additive upstream fields should not break parsing (`extra="ignore"`), but newly
  selected fields must be typed and documented. Use `get_variant_to_file` for
  annotations too large for LLM context.

## Scope notes

- Ensembl beta is **multi-backend**, not a single GraphQL URL. Official help docs
  mostly describe `/data/graphql` (core) and `/data/refget`; the website also uses
  `/api/graphql/variation` (hypsipyle), `/api/graphql/compara`, metadata/search/tools
  REST, and more. See [docs/ensembl_beta_backends.md](docs/ensembl_beta_backends.md).
- This MCP wraps core GraphQL, variation GraphQL, compara homologies, metadata
  releases, legacy REST rsID resolution, and Refget. Bare rsIDs are resolved to
  all matching assembly coordinates before hypsipyle receives `chr:pos:rsid`.
- Structural variants and AlphaMissense/ESM1b are not available from the wrapped
  variation API. PolyPhen may appear on transcript consequences. Compara is wired
  but currently returns empty lists for
  known human genes due to an upstream data-loading issue.
- Most lookups require a `genome_id` (UUID). The human reference genome_id default is
  `a7335667-93e7-11ec-a39d-005056b38ce3`. Use `find_genomes` to resolve other species.
- Current core GraphQL `sequence` fields expose sequence metadata such as alphabet
  and checksum, not raw nucleotide/amino-acid strings. Use Refget tools for raw
  sequence retrieval.
- `get_protein_sequence` bridges gene symbol → canonical transcript → product
  checksum → Refget sequence in one call. Also accepts a product stable ID directly.
- `get_variant_clinical_summary` distills a full variant annotation into a compact
  view: filtered population frequencies (default: gnomADe:ALL, gnomADg:ALL,
  1000GENOMES:phase_3:ALL), per-allele CADD, per-consequence SIFT/PolyPhen/max
  SpliceAI delta, and phenotype associations. Accepts custom `populations` list.
- `get_variants_in_region` returns all short variants overlapping a genomic interval
  via Ensembl REST, including rsIDs, consequence types, and clinical significance.
- `get_gene_phenotypes` retrieves disease/phenotype associations from ClinVar,
  OMIM, GWAS catalog, Cancer Gene Census, and other sources.
- `variant_recoder` converts between rsID, HGVS (genomic/coding/protein), SPDI,
  and VCF representations.

## Enriched field selections

Gene lookups (`find_genes_by_symbol`, `get_gene_by_id`) now include:
- `external_references` with source name, accession, URL, and assignment method.
- `alternative_symbols` (e.g. FANCD1 for BRCA2).
- `metadata.name` (HGNC accession) and `metadata.biotype`.
- Nested `transcripts[]` with MANE Select/Plus Clinical flags, canonical, APPRIS, TSL.

Transcript lookups (`get_transcript`) now include:
- `spliced_exons[]` with index, relative location, and genomic coordinates per exon.
- `product_generating_contexts[]` with CDS (protein_length, nucleotide_length),
  5'/3' UTR boundaries, and product with Refget checksum.
- Full `metadata` (MANE, canonical, APPRIS, TSL, gencode_basic).
- `external_references` and `relative_location`.

Product lookups (`get_product_by_id`) now include:
- `sequence.checksum` and `sequence.alphabet` for Refget bridging.
- `family_matches[]` (Pfam, PANTHER) with domain positions, scores, e-values.
- `external_references` with full source info (PDB, UniProt, Reactome, etc.).

Variant prediction results include `qualifier { result_type modes }` to make
SpliceAI delta scores interpretable (e.g. "Delta score for acceptor gain").
