---
name: ensembl-species-genome
description: Resolve a species or assembly to its Ensembl genome_id. Use when a user asks about a non-human organism (mouse, zebrafish, etc.), needs a genome_id for a species, or wants genome/assembly metadata.
---

# Ensembl species and genome resolution

Use the Ensembl MCP tools to resolve species and assemblies.

## Example user queries

- "What is the genome_id for mouse?"
- "Look up BRCA2 in zebrafish."
- "Find the Danio rerio assembly in Ensembl."
- "What assemblies are available for Mus musculus?"

## How to answer

1. Most Ensembl lookups require a `genome_id` (a UUID). Human GRCh38 defaults to
   `a7335667-93e7-11ec-a39d-005056b38ce3` and is used automatically when omitted.
2. For other species, call `find_genomes` with one of:
   - `scientific_name`: e.g. "Mus musculus", "Danio rerio"
   - `common_name`: e.g. "mouse", "zebrafish"
   - `ensembl_name`: e.g. "homo_sapiens"
   - `assembly_accession_id`: e.g. "GCA_000001405.29"
   - `species_taxonomy_id`: NCBI taxonomy ID as a string
   - `tolid`: Tree of Life identifier
3. To get full metadata for a known genome_id, call `get_genome`.
4. The search can be slow on Ensembl beta. Resolve the genome_id once and reuse
   it for all subsequent lookups in the same species/assembly.
5. When presenting results, show the genome_id, scientific name, common name,
   assembly accession, and whether it is the reference assembly.
6. Pass the resolved genome_id to all other tools (`find_genes_by_symbol`,
   `get_transcript`, `get_variant`, etc.) when working with non-human species.
