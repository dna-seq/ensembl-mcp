---
name: ensembl-variant-conversion
description: Convert variants between rsID, HGVS (genomic/coding/protein), SPDI, and VCF formats. Use when a user asks "convert rs28934578 to HGVS notation", "what is the protein change for this variant", or wants to translate between coordinate systems.
---

# Ensembl variant conversion

Use the Ensembl MCP tools to convert variant identifiers between formats.

## Example user queries

- "Convert rs28934578 to HGVS notation."
- "What is the protein HGVS for rs699?"
- "Give me the SPDI notation for this variant."
- "Convert ENST00000366667.6:c.776T>C back to an rsID."

## How to answer

1. Call `variant_recoder` with any supported input:
   - rsID: `rs699`
   - HGVS coding: `ENST00000366667.6:c.776T>C`
   - HGVS genomic: `1:g.230710048A>G`
   - SPDI: `1:230710047:A:G`
2. The result includes all equivalent representations:
   - `hgvsc`: coding HGVS (transcript-relative).
   - `hgvsp`: protein HGVS (amino acid change, e.g. `p.Met259Thr`).
   - `hgvsg`: genomic HGVS.
   - `spdi`: SPDI notation (sequence:position:deletion:insertion).
   - `id`: associated rsIDs.
3. Results are grouped by allele. For multiallelic sites, each alternate allele
   gets its own entry.
4. When presenting conversions, show all available formats in a clear table or
   list. Highlight the protein-level change (hgvsp) when present, as it is often
   the most biologically meaningful.
5. For coordinate resolution without full recoding, use `resolve_rsid` or
   `batch_resolve_rsids` instead.
