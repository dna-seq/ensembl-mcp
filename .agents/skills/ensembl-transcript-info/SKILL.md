---
name: ensembl-transcript-info
description: Retrieve transcript details including exon count, exon coordinates, MANE Select status, CDS length, and protein product. Use when a user asks "how many exons does BRCA2 have", "is this transcript MANE Select", "what is the CDS length", or about transcript structure.
---

# Ensembl transcript info

Use the Ensembl MCP tools for transcript-level queries.

## Example user queries

- "How many exons does the canonical BRCA2 transcript have? What is the CDS length?"
- "Is ENST00000380152 the MANE Select transcript?"
- "What are the exon coordinates for BRCA2-201?"
- "What protein does transcript ENST00000269305 encode?"

## How to answer

1. For a known transcript stable ID (e.g. `ENST00000380152`), call `get_transcript`
   with `stable_id`. For a transcript symbol (e.g. `BRCA2-201`), use `symbol` instead.
2. For searching transcripts by identifier across genomes, call `transcript_search`.
3. The result includes:
   - `metadata.mane`: MANE Select or Plus Clinical designation with NCBI transcript ID.
   - `metadata.canonical`: whether this is the Ensembl canonical transcript.
   - `metadata.appris` and `metadata.tsl`: APPRIS principal annotation and TSL level.
   - `spliced_exons[]`: each exon with index, stable ID, and genomic coordinates.
   - `product_generating_contexts[]`: CDS with protein_length, 5'/3' UTR boundaries,
     and linked protein product with Refget sequence checksum.
   - `external_references`: RefSeq, CCDS, and other cross-references.
4. When reporting exon structure, include the total exon count and genomic coordinate
   span. For the protein product, mention the stable ID and length.
5. To retrieve the actual protein sequence, use `get_protein_sequence` or bridge
   through the Refget checksum with `get_sequence`.
