---
name: ensembl-variant-lookup
description: Resolve and annotate rsIDs or coordinate-form short variants. Use when a user asks "what are the coordinates for rs699", "resolve rs55960271 to GRCh38", "annotate this variant", or wants alleles, frequencies, consequences, phenotype assertions, or prediction scores.
---

# Ensembl variant lookup

Use the Ensembl MCP tools rather than guessing coordinates or annotations.

## Example user queries

- "What are the genomic coordinates and alleles for variant rs55960271 in human?"
- "Resolve rs587777516 to its GRCh38 coordinates. Give me the chromosome, position, and alleles."
- "Where is rs1063192 located in the human genome?"
- "Use the full live annotation for human rs55960271. State the affected gene, at least one phenotype association, and the phenotype source."
- "Resolve rs699, rs28934578, and rs55960271 to their chromosomes and alleles."

## How to answer

1. For a bare dbSNP identifier such as `rs699`, call `get_variant_by_rsid`. It
   resolves the current assembly mapping and then queries variation GraphQL.
2. For many bare identifiers, call `batch_get_variants_by_rsid`. If only
   coordinates are needed, use `resolve_rsid` or `batch_resolve_rsids`.
3. To resolve many exact genomic coordinates to overlapping variants and rsIDs,
   call `batch_resolve_coordinates` with `region:position` values.
4. For an existing `region:position:rsid` identifier, call `get_variant`.
5. Use `list_variant_populations` to explain frequency-panel names. State the
   exact population alongside each frequency; do not treat global and ancestry
   populations as interchangeable.
6. Summarize reference/alternate alleles, genomic location, affected genes and
   transcripts, molecular consequences, phenotype evidence, and available
   prediction methods. Distinguish CADD, SIFT, SpliceAI, GERP, and VEP rather
   than combining their scores.
7. Report every assembly mapping if resolution is ambiguous. Do not silently
   choose the first mapping.
8. For a large full annotation, use `get_variant_to_file`.

Do not claim support for AlphaMissense, ESM1b, or general structural variants;
the wrapped variation API does not currently provide them. PolyPhen may appear
on transcript consequences. Variant annotations and prediction scores are
evidence, not a diagnosis.
