---
name: ensembl-gene-lookup
description: Look up genes by symbol, name, or Ensembl stable ID. Use when a user asks "tell me about BRCA2", "which chromosome contains TP53", "what is the Ensembl ID for a gene", or wants to find multiple genes at once.
---

# Ensembl gene lookup

Use the Ensembl MCP tools to look up gene information rather than relying on training data.

## Example user queries

- "Tell me about BRCA2."
- "Which human chromosome contains BRCA2?"
- "In human, I mean the tumor protein p53 gene. Give me its HGNC symbol, Ensembl gene stable id, and chromosome."
- "Resolve BRCA2, TP53, and EGFR and tell me their chromosomes."

## How to answer

1. For a gene symbol such as `BRCA2` or `TP53`, call `find_genes_by_symbol`.
   Returns HGNC accession, biotype, alternative symbols (e.g. FANCD1 for BRCA2),
   cross-references (UniProt, RefSeq, OMIM, Expression Atlas), and all transcripts
   with MANE Select/canonical flags.
2. For an Ensembl stable ID such as `ENSG00000139618`, call `get_gene_by_id`.
   Accepts both versioned (`ENSG00000139618.18`) and unversioned IDs.
3. For many gene symbols at once, call `bulk_find_genes`. It reports progress and
   separates found genes from missing symbols.
4. Most lookups default to human (`genome_id = a7335667-93e7-11ec-a39d-005056b38ce3`).
   For other species, resolve the genome_id first with `find_genomes`.
5. Present the gene's location (chromosome, start, end, strand), biotype, and
   transcript count. Mention MANE Select transcripts and notable cross-references
   when they exist.
6. If the user wants deeper transcript or protein detail, follow up with
   `get_transcript` or `get_product_by_id` as appropriate.
