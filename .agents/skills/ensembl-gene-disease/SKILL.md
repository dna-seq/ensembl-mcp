---
name: ensembl-gene-disease
description: Retrieve disease and phenotype associations for a gene from ClinVar, OMIM, GWAS catalog, and Cancer Gene Census. Use when a user asks "what diseases are associated with TP53", "is BRCA2 linked to cancer", or about gene-disease relationships.
---

# Ensembl gene-disease associations

Use the Ensembl MCP tools for gene-phenotype and gene-disease queries.

## Example user queries

- "What diseases are associated with TP53?"
- "Is BRCA2 linked to any hereditary conditions?"
- "What phenotypes does CLCN1 cause?"
- "Show me ClinVar associations for EGFR."

## How to answer

1. Call `get_gene_phenotypes` with a gene symbol (e.g. `TP53`) or Ensembl gene ID.
2. Returns associations from multiple sources:
   - ClinVar: clinical significance of gene variants.
   - OMIM: Mendelian disease associations.
   - GWAS catalog: genome-wide association study hits.
   - Cancer Gene Census: cancer gene classifications.
   - Other sources with PubMed references when available.
3. When presenting results:
   - Group by source for clarity.
   - Highlight the most clinically significant associations first.
   - Note the total count; some well-studied genes (e.g. TP53 has 443
     associations) have hundreds.
   - Include PubMed references when available for traceability.
4. For variant-specific disease associations (rather than gene-level), use
   `get_variant_clinical_summary` or the full `get_variant_by_rsid` annotation
   which includes `phenotype_assertions` per allele.
5. These are sourced associations, not diagnostic conclusions. Always cite the
   source database.
