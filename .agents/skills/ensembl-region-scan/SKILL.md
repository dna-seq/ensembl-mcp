---
name: ensembl-region-scan
description: Scan a genomic region for genes, transcripts, and variants. Use when a user asks "what gene is at position X on chromosome Y", "what gene overlaps this locus", "what clinically significant variants are in BRCA2", or wants to explore a genomic interval.
---

# Ensembl region scan

Use the Ensembl MCP tools to explore genomic intervals.

## Example user queries

- "What gene is at position 143,351,678 on chromosome 7?"
- "For the human locus chr13:32315086-32400268, which gene overlaps it?"
- "What gene overlaps position 143351678 on chromosome 7 in the human genome?"
- "What clinically significant variants are in BRCA2 exon 11?"

## How to answer

1. To find genes and transcripts overlapping a region, call `overlap_region` with
   `region_name` (chromosome, e.g. "13"), `start`, and `end`.
2. To find all known short variants in a region, call `get_variants_in_region`.
   Returns rsIDs, alleles, consequence types, clinical significance, and source.
   Large intervals (>1 Mb) may return thousands of variants.
3. To get metadata about a chromosome or region itself, call `get_region`.
4. Coordinates use 1-based inclusive Ensembl convention.
5. A common workflow: use `find_genes_by_symbol` to get a gene's coordinates,
   then `get_variants_in_region` over that span to find all catalogued variants.
6. When presenting region results:
   - State the chromosome, start, end, and total feature count.
   - For gene overlaps, list gene symbols, Ensembl gene stable IDs, and biotypes.
   - For variant scans, highlight clinically significant variants and summarize
     the consequence type distribution.
7. For very gene-dense or variant-dense regions, suggest narrowing the interval
   or using file-output tools to avoid overwhelming LLM context.
