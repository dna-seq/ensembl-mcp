---
name: ensembl-sequence-retrieval
description: Retrieve raw nucleotide or amino acid sequences via GA4GH Refget. Use when a user asks "give me the protein sequence of BRCA2", "fetch a subsequence by checksum", or wants raw sequence data for a gene or product.
---

# Ensembl GA4GH Refget sequence retrieval

Use the Ensembl MCP tools for raw sequence access via the GA4GH Refget protocol.

## Example user queries

- "Give me the amino acid sequence of TP53."
- "Fetch the first 50 residues of ENSP00000369497."
- "What is the sequence for checksum 6681ac2f62509cfc220d78751b8dc524?"
- "Save the full BRCA2 protein sequence to a file."

## How to answer

1. To get a protein sequence by gene name in one step, call `get_protein_sequence`
   with `gene_symbol`. It resolves gene -> canonical transcript -> product
   checksum -> Refget sequence in a single call. Also accepts `product_stable_id`.
2. For small sequences that fit in LLM context, call `get_sequence` with the
   sequence digest ID (MD5 or ga4gh SQ. prefix). Use `start` and `end` for
   subsequences (0-indexed, half-open).
3. For large sequences, call `get_sequence_to_file` to stream the result to a
   local file instead of returning it into context.
4. To check sequence length, aliases, and cross-authority identifiers, call
   `get_sequence_metadata`.
5. Sequence checksums are found in:
   - `product.sequence.checksum` from `get_product_by_id` or `get_transcript`.
   - `get_protein_sequence` result includes the checksum used.
6. When presenting sequences:
   - State the sequence length and alphabet (nucleotide or amino acid).
   - For subsequences, state the coordinates used.
   - For very long sequences (>1000 residues), suggest using the file output
     variant or requesting a subsequence.
7. Current core GraphQL `sequence` fields expose metadata (alphabet, checksum),
   not raw strings. Always use Refget tools for the actual sequence.
