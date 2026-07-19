# Variant Validation in Agentic Workflows

LLMs routinely hallucinate genomic coordinates, rsIDs, alleles, and gene
associations. In agentic pipelines that reason about variants -- polygenic risk
score interpretation, clinical report drafting, pharmacogenomics -- a single
wrong coordinate or invented rsID can silently corrupt downstream analysis.

This MCP server provides ground-truth validation by resolving identifiers
against the live Ensembl database. Two complementary directions are supported.

## rsID to coordinates, alleles, and annotation

Given a bare rsID, `resolve_rsid` maps it to every GRCh38 coordinate, and
`get_variant_by_rsid` adds full annotation (alleles, population frequencies,
phenotype assertions, prediction scores).

## Coordinates to gene and variant context

Given a genomic position, `overlap_region` identifies every gene and transcript
that spans it.

## Why this matters for agents

| Failure mode | Without validation | With ensembl-mcp |
| --- | --- | --- |
| Hallucinated rsID | Agent invents rs999999999; pipeline silently uses it | `resolve_rsid` returns empty mappings; agent reports the ID is invalid |
| Wrong chromosome | Agent claims rs1063192 is on chr2 | `resolve_rsid` returns chr9:22003368; agent self-corrects |
| Stale coordinates | Agent uses GRCh37 position from training data | Live GRCh38 mappings returned; assembly mismatch is caught |
| Invented gene link | Agent associates a variant with the wrong gene | `overlap_region` returns the actual gene(s) at that locus |

## Validating a PRS variant list

When interpreting polygenic risk scores, an agent may receive a list of rsIDs
from a scoring file and need to verify each one before reporting:

```bash
uvx --from ensembl-mcp ensembl-mcp agent \
  "Resolve these variant rsIDs to their human GRCh38 chromosomes: \
   rs55960271, rs587777516, rs1063192. For each, give the chromosome number."
```

The server batch-resolves all three and returns verified coordinates. A curated
test fixture at `data/test/pathogenic_snps.json` with 7 ClinVar-annotated
pathogenic SNPs verifies both resolution directions in the agentic integration
tests.

## Large and raw payloads

Most tools return compact metadata. For large sequence data, use the file-writing
tools:

- `get_sequence_to_file` -- streams a Refget sequence to disk
- `get_variant_to_file` -- writes a full variant annotation to JSON
- `graphql_query_to_file` -- writes raw GraphQL results to a file

Files are written under `ENSEMBL_MCP_OUTPUT_DIR` (default `.ensembl_mcp_outputs`)
and only path/size metadata is returned to the LLM context.
