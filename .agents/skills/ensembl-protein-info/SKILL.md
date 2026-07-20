---
name: ensembl-protein-info
description: Look up protein products, domains, sequences, and cross-references. Use when a user asks "what domains does TP53 have", "give me the amino acid sequence of BRCA2", "what is ENSP00000369497", or about Pfam/UniProt/PDB links.
---

# Ensembl protein info

Use the Ensembl MCP tools for protein-level queries.

## Example user queries

- "Give me the amino acid sequence of TP53."
- "What domains does the TP53 protein have?"
- "ENSP00000369497.3 is an Ensembl product stable id. What product type is it, and what is its length?"
- "What is the UniProt accession for BRCA2 protein?"

## How to answer

1. For a protein stable ID (e.g. `ENSP00000369497.3`), call `get_product_by_id`.
   Returns domain annotations (`family_matches` from Pfam, PANTHER with positions
   and e-values), cross-references (PDB, UniProt, Reactome, BioGRID, Human Protein
   Atlas), and the Refget sequence checksum.
2. To get the amino acid sequence for a gene, call `get_protein_sequence` with
   `gene_symbol`. It bridges gene -> canonical transcript -> product -> Refget
   sequence in a single call. Also accepts `product_stable_id` directly.
3. For large sequences that should not be returned into LLM context, use
   `get_sequence_to_file` with the protein's Refget checksum.
4. When presenting results, highlight:
   - Protein length and biotype.
   - Notable domain hits (Pfam, PANTHER) with their positions and descriptions.
   - Key cross-references: UniProt accession, PDB structures, Reactome pathways.
   - MANE Select status of the parent transcript if available.
5. The `sequence.checksum` field can be used with `get_sequence` or
   `get_sequence_metadata` for further Refget operations.
