---
name: ensembl-clinical-variant
description: Get clinical variant summaries with population frequencies, pathogenicity predictions, and disease associations. Use when a user asks "is rs699 pathogenic", "what are the population frequencies of this variant", "what do we know about the TP53 R175H mutation", or about CADD/SIFT/PolyPhen scores.
---

# Ensembl clinical variant summary

Use the Ensembl MCP tools for clinically-oriented variant queries.

## Example user queries

- "What is rs699? Is it pathogenic? What are its population frequencies?"
- "What do we know about the TP53 R175H mutation (rs28934578)?"
- "How does rs699 frequency vary across populations?"
- "Inspect the full live human annotation for rs699. Report its GRCh38 coordinate, reference and alternate alleles, affected gene, one frequency for the G allele with the exact population name, and group available prediction methods by variant, allele, and transcript-consequence level."

## How to answer

1. For a clinical overview of a variant, call `get_variant_clinical_summary` with
   the rsID. It resolves the rsID, fetches full annotation, and distills:
   - Variant-level predictions (VEP, GERP, AncestralAllele).
   - Per-allele CADD scores.
   - Filtered population frequencies (default: gnomADe:ALL, gnomADg:ALL,
     1000GENOMES:phase_3:ALL). Pass `populations` for specific panels.
   - Phenotype associations with source (ClinVar, OMIM, etc.).
   - Per-consequence SIFT, PolyPhen, and max SpliceAI delta scores.
2. To request specific population panels, pass them as `populations`, e.g.
   `["gnomADe:afr", "gnomADe:nfe", "gnomADg:ALL"]`.
3. To see all available population panels, call `list_variant_populations`.
4. When presenting results:
   - Always cite the population name alongside each frequency.
   - Distinguish prediction methods: CADD is allele-level, SIFT and PolyPhen are
     transcript-consequence-level, SpliceAI delta is per splice site type.
   - GERP and AncestralAllele are variant-level. Do not combine scores from
     different methods.
   - State phenotype source (ClinVar, OMIM, GWAS catalog).
   - Note that predictions are evidence, not a diagnosis.
5. For the full unfiltered annotation, use `get_variant_by_rsid` with `full=True`,
   or `get_variant_to_file` for very large payloads.
