# Architecture and Refget Integration

This document describes the modular trait-based architecture of the `ensembl-mcp` client and the integration of the GA4GH Refget sequence retrieval services.

---

## Modular Trait-Based Architecture

To maintain a clean separation of concerns, the `EnsemblGraphQLClient` is designed using Python's cooperative multiple inheritance (mixins/traits). This decouples the GraphQL metadata queries from the REST-based GA4GH Refget sequence retrieval.

```
       +---------------------+        +--------------------+
       | EnsemblGraphQLTrait |        | EnsemblRefgetTrait |
       +----------+----------+        +---------+----------+
                  ^                             ^
                  |                             |
                  +--------------+--------------+
                                 |
                     +-----------+-----------+
                     | EnsemblGraphQLClient  |
                     +-----------------------+
```

### 1. `EnsemblGraphQLTrait`
Responsible for all communication with the Ensembl Beta Core GraphQL API.
*   **Endpoint**: `https://beta.ensembl.org/data/graphql/core`
*   **Capabilities**:
    *   Executes arbitrary GraphQL queries via `execute()`.
    *   Handles GraphQL-specific errors (parsing the `errors` payload and raising `GraphQLError`).
    *   Supports custom timeouts and endpoint overrides.

### 2. `EnsemblRefgetTrait`
Responsible for all sequence-level operations complying with the Global Alliance for Genomics and Health (GA4GH) Refget specification.
*   **Endpoint**: `https://beta.ensembl.org/data/refget`
*   **Capabilities**:
    *   Retrieves raw nucleotide or amino acid sequences by cryptographic checksum (MD5 or ga4gh `SQ.` prefix) via `fetch_sequence()`.
    *   Supports efficient subsequence slicing via `start` and `end` query parameters.
    *   Streams large sequences directly to local files via `fetch_sequence_to_file()`.
    *   Retrieves sequence metadata and cross-authority aliases (UCSC, INSDC, RefSeq, Ensembl) via `fetch_sequence_metadata()`.

### 3. `EnsemblGraphQLClient`
The unified client that inherits from both traits. This client is used throughout the CLI, the MCP server, and the Agno agent to provide complete access to both annotation metadata and raw sequence data.

---

## GA4GH Refget Sequence Retrieval

The GA4GH Refget API standardizes how biological sequences are identified and distributed. Rather than relying on a centralized naming authority (like Ensembl, UCSC, or NCBI), Refget uses cryptographic digests of the sequence string itself.

### Key Features

1.  **Authority-Free Identification**: If two different databases have the exact same sequence, they will compute the exact same MD5 or SHA-512 digest. This guarantees sequence identity and provenance.
2.  **Subsequence Slicing**: Large sequences (such as whole human chromosomes) can be sliced on the server side using `start` and `end` coordinates. The client only downloads the requested slice, saving bandwidth and memory.
3.  **Cross-Reference Aliases**: The metadata endpoint maps a sequence digest to all of its known names across different databases (e.g., mapping a digest to UCSC `chr13`, INSDC `CM000675.2`, and RefSeq `NC_000013.11`).

### Refget MCP Tools

The following tools are exposed by the MCP server to interact with the Refget service:

*   `get_sequence(sequence_id: str, start: int | None = None, end: int | None = None) -> str`
    *   Retrieves a raw sequence or subsequence as a plain text string.
*   `get_sequence_to_file(sequence_id: str, output_name: str, start: int | None = None, end: int | None = None) -> dict`
    *   Streams a sequence or subsequence directly to a local file under the configured output directory.
*   `get_sequence_metadata(sequence_id: str) -> dict`
    *   Retrieves metadata, including sequence length and cross-authority aliases.

---

## Variant Resolution and Refget

A common question is whether Refget can be used to resolve variant information (like looking up an rsid or fetching allele frequencies).

*   **Refget's Role**: Refget is strictly for **reference sequences**. It does not store variant databases.
*   **VRS Integration**: However, Refget is a fundamental building block for the **GA4GH Variation Representation Specification (VRS)**. VRS requires that all variants are anchored to reference sequences identified by their Refget digest (prefixed with `SQ.`). This ensures that variant descriptions remain unambiguous regardless of which genome assembly or naming convention is used.
*   **Resolving Variants**: To perform actual variant resolution (such as VEP annotation or rsid lookups), you must use a dedicated variation service (such as Ensembl's `ensembl-hypsipyle` or the Ensembl REST API variation endpoints).
