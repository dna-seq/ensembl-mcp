import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eliot import start_action
from fastmcp import Context, FastMCP
from fastmcp.utilities.tasks import TaskConfig

from ensembl_mcp import queries
from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import HUMAN_GENOME_ID, Settings, get_settings
from ensembl_mcp.models import GenomeKeywordInput

# Every data tool may run synchronously or be promoted to a background task by
# the client (the MCP background-task protocol, SEP-1686).
TASK = TaskConfig(mode="optional")


async def op_version(client: EnsemblGraphQLClient) -> dict[str, Any]:
    data = await client.execute(queries.VERSION_QUERY)
    return data["version"]


async def op_find_genes_by_symbol(
    client: EnsemblGraphQLClient, symbol: str, genome_id: str
) -> list[dict[str, Any]]:
    data = await client.execute(
        queries.GENES_BY_SYMBOL_QUERY,
        {"symbol": symbol, "genome_id": genome_id},
    )
    return data.get("genes") or []


async def op_get_gene_by_id(
    client: EnsemblGraphQLClient, genome_id: str, stable_id: str
) -> dict[str, Any] | None:
    data = await client.execute(
        queries.GENE_BY_ID_QUERY,
        {"genome_id": genome_id, "stable_id": stable_id},
    )
    return data.get("gene")


async def op_get_transcript(
    client: EnsemblGraphQLClient,
    genome_id: str,
    stable_id: str | None = None,
    symbol: str | None = None,
) -> dict[str, Any] | None:
    if stable_id is None and symbol is None:
        raise ValueError("Provide either stable_id or symbol to look up a transcript.")
    if stable_id is not None:
        data = await client.execute(
            queries.TRANSCRIPT_BY_ID_QUERY,
            {"genome_id": genome_id, "stable_id": stable_id},
        )
    else:
        data = await client.execute(
            queries.TRANSCRIPT_BY_SYMBOL_QUERY,
            {"genome_id": genome_id, "symbol": symbol},
        )
    return data.get("transcript")


async def op_transcript_search(
    client: EnsemblGraphQLClient,
    query: str,
    genome_ids: list[str],
    page: int = 1,
    per_page: int = 10,
) -> dict[str, Any]:
    payload = {
        "genome_ids": genome_ids,
        "query": query,
        "page": page,
        "per_page": per_page,
    }
    data = await client.execute(queries.TRANSCRIPT_SEARCH_QUERY, {"payload": payload})
    return data.get("transcript_search") or {"meta": None, "matches": []}


async def op_get_product_by_id(
    client: EnsemblGraphQLClient, genome_id: str, stable_id: str
) -> dict[str, Any] | None:
    data = await client.execute(
        queries.PRODUCT_BY_ID_QUERY,
        {"genome_id": genome_id, "stable_id": stable_id},
    )
    return data.get("product")


async def op_get_region(
    client: EnsemblGraphQLClient, genome_id: str, name: str
) -> dict[str, Any] | None:
    data = await client.execute(
        queries.REGION_BY_NAME_QUERY,
        {"genome_id": genome_id, "name": name},
    )
    return data.get("region")


async def op_overlap_region(
    client: EnsemblGraphQLClient,
    genome_id: str,
    region_name: str,
    start: int,
    end: int,
) -> dict[str, Any]:
    data = await client.execute(
        queries.OVERLAP_REGION_QUERY,
        {"genome_id": genome_id, "region_name": region_name, "start": start, "end": end},
    )
    return data.get("overlap_region") or {"genes": [], "transcripts": []}


async def op_find_genomes(
    client: EnsemblGraphQLClient, keyword: GenomeKeywordInput
) -> list[dict[str, Any]]:
    data = await client.execute(
        queries.GENOMES_BY_KEYWORD_QUERY,
        {"keyword": keyword.to_graphql_input()},
    )
    return data.get("genomes") or []


async def op_get_genome(
    client: EnsemblGraphQLClient, genome_id: str
) -> dict[str, Any] | None:
    data = await client.execute(queries.GENOME_BY_ID_QUERY, {"genome_id": genome_id})
    return data.get("genome")


def _default_graphql_output_name(
    query: str, variables: dict[str, Any] | None = None
) -> str:
    payload = json.dumps({"query": query, "variables": variables or {}}, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"ensembl_graphql_{timestamp}_{digest}.json"


def _default_sequence_output_name(
    sequence_id: str,
    start: int | None = None,
    end: int | None = None,
) -> str:
    payload = json.dumps(
        {"sequence_id": sequence_id, "start": start, "end": end},
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"refget_sequence_{timestamp}_{digest}.txt"


def _resolve_output_path(
    output_dir: str,
    output_name: str | None,
    default_name: str,
    suffix: str,
) -> Path:
    directory = Path(output_dir).expanduser()
    filename = output_name or default_name
    path = Path(filename)
    if path.name != filename:
        raise ValueError("output_name must be a filename, not a path.")
    if path.suffix != suffix:
        path = path.with_suffix(suffix)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / path


async def op_graphql_query_to_file(
    client: EnsemblGraphQLClient,
    query: str,
    variables: dict[str, Any] | None,
    output_dir: str,
    output_name: str | None = None,
) -> dict[str, Any]:
    """Run a GraphQL query and write the JSON data payload to a local file."""
    output_path = _resolve_output_path(
        output_dir,
        output_name,
        _default_graphql_output_name(query, variables),
        ".json",
    )
    data = await client.execute(query, variables)
    encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    output_path.write_bytes(encoded)
    return {
        "path": str(output_path),
        "bytes": len(encoded),
        "keys": sorted(data.keys()),
    }


async def op_bulk_find_genes(
    client: EnsemblGraphQLClient,
    symbols: list[str],
    genome_id: str,
    ctx: Context | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Resolve many gene symbols at once, reporting progress as it goes."""
    found: list[dict[str, Any]] = []
    missing: list[str] = []
    total = len(symbols)
    with start_action(action_type="bulk_find_genes", count=total, genome_id=genome_id):
        for index, symbol in enumerate(symbols, start=1):
            genes = await op_find_genes_by_symbol(client, symbol, genome_id)
            if genes:
                found.extend(genes)
            else:
                missing.append(symbol)
            if ctx is not None:
                await ctx.report_progress(
                    progress=index, total=total, message=f"Resolved {symbol}"
                )
    return {"found": found, "missing": [{"symbol": s} for s in missing]}


async def op_get_sequence(
    client: EnsemblGraphQLClient,
    sequence_id: str,
    start: int | None = None,
    end: int | None = None,
) -> str:
    return await client.fetch_sequence(sequence_id, start, end)


async def op_get_sequence_to_file(
    client: EnsemblGraphQLClient,
    sequence_id: str,
    output_dir: str,
    start: int | None = None,
    end: int | None = None,
    output_name: str | None = None,
) -> dict[str, Any]:
    output_path = _resolve_output_path(
        output_dir,
        output_name,
        _default_sequence_output_name(sequence_id, start, end),
        ".txt",
    )
    bytes_written = await client.fetch_sequence_to_file(
        sequence_id, output_path, start, end
    )
    return {
        "path": str(output_path),
        "bytes": bytes_written,
        "sequence_id": sequence_id,
        "start": start,
        "end": end,
    }


async def op_get_sequence_metadata(
    client: EnsemblGraphQLClient,
    sequence_id: str,
) -> dict[str, Any]:
    return await client.fetch_sequence_metadata(sequence_id)


def create_server(settings: Settings | None = None) -> FastMCP:
    """Build and configure the Ensembl GraphQL MCP server."""
    settings = settings or get_settings()
    client = EnsemblGraphQLClient(settings)
    mcp: FastMCP = FastMCP(
        "ensembl-mcp",
        instructions=(
            "Query the Ensembl beta GraphQL API for genes, transcripts, proteins, "
            "regions and genomes, and retrieve raw sequences or sequence metadata "
            "via the GA4GH Refget API. Most lookups need a genome_id (a UUID); use "
            "find_genomes to resolve a species name to its genome_id. The human "
            f"reference genome_id is {settings.human_genome_id}."
        ),
    )

    @mcp.tool(task=TASK)
    async def get_version() -> dict[str, Any]:
        """Return the Ensembl GraphQL API version.

        Example:
            get_version()
            -> {"api": {"major": "0", "minor": "2", "patch": "0-beta"}}
        """
        return await op_version(client)

    @mcp.tool(task=TASK)
    async def get_sequence(
        sequence_id: str,
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        """Retrieve a raw biological sequence or subsequence by its digest ID.

        The sequence_id can be a cryptographic digest (such as MD5 or ga4gh SQ. prefix).
        Use start and end (0-indexed, half-open) to request a subsequence.

        Example:
            get_sequence(sequence_id="6681ac2f62509cfc220d78751b8dc524", start=1, end=20)
            -> "AAGTCT..."
        """
        return await op_get_sequence(client, sequence_id, start, end)

    @mcp.tool(task=TASK)
    async def get_sequence_to_file(
        sequence_id: str,
        start: int | None = None,
        end: int | None = None,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Stream a Refget sequence or subsequence to a local text file.

        Use this instead of ``get_sequence`` when retrieving a large sequence
        that should not be returned directly into an LLM context. Files are
        written under ``ENSEMBL_MCP_OUTPUT_DIR``. ``output_name`` must be a
        filename, not a path.

        Example:
            get_sequence_to_file(
                sequence_id="6681ac2f62509cfc220d78751b8dc524",
                start=0,
                end=20,
                output_name="refget_sequence.txt",
            )
            -> {"path": ".ensembl_mcp_outputs/refget_sequence.txt",
                "bytes": 20, "sequence_id": "...", "start": 0, "end": 20}
        """
        return await op_get_sequence_to_file(
            client, sequence_id, settings.output_dir, start, end, output_name
        )

    @mcp.tool(task=TASK)
    async def get_sequence_metadata(sequence_id: str) -> dict[str, Any]:
        """Retrieve metadata and cross-authority aliases for a sequence digest ID.

        Example:
            get_sequence_metadata(sequence_id="6681ac2f62509cfc220d78751b8dc524")
            -> {"metadata": {"length": 12345, "aliases": [{"naming_authority": "ensembl", "alias": "..."}]}}
        """
        return await op_get_sequence_metadata(client, sequence_id)

    @mcp.tool(task=TASK)
    async def find_genes_by_symbol(
        symbol: str, genome_id: str = HUMAN_GENOME_ID
    ) -> list[dict[str, Any]]:
        """Find genes by their display symbol (e.g. ``BRCA2``) in a genome.

        Example:
            find_genes_by_symbol(symbol="BRCA2")
            -> [{"stable_id": "ENSG00000139618.18", "symbol": "BRCA2",
                 "name": "BRCA2 DNA repair associated", "so_term": "protein_coding",
                 "transcript_count": 15,
                 "slice": {"region": {"name": "13"},
                           "location": {"start": 32315086, "end": 32400268},
                           "strand": {"code": "forward", "value": 1}}}]
        """
        return await op_find_genes_by_symbol(client, symbol, genome_id)

    @mcp.tool(task=TASK)
    async def get_gene_by_id(
        stable_id: str, genome_id: str = HUMAN_GENOME_ID
    ) -> dict[str, Any] | None:
        """Get a gene by its Ensembl stable id (e.g. ``ENSG00000139618``).

        The stable id may be unversioned (``ENSG00000139618``) or versioned
        (``ENSG00000139618.18``).

        Example:
            get_gene_by_id(stable_id="ENSG00000139618")
            -> {"stable_id": "ENSG00000139618.18", "symbol": "BRCA2",
                "so_term": "protein_coding", "transcript_count": 15, ...}
        """
        return await op_get_gene_by_id(client, genome_id, stable_id)

    @mcp.tool(task=TASK)
    async def get_transcript(
        stable_id: str | None = None,
        symbol: str | None = None,
        genome_id: str = HUMAN_GENOME_ID,
    ) -> dict[str, Any] | None:
        """Get a transcript by stable id or symbol (provide one of them).

        Example:
            get_transcript(stable_id="ENST00000380152")
            -> {"stable_id": "ENST00000380152.8", "symbol": "BRCA2-201",
                "so_term": "protein_coding",
                "slice": {"region": {"name": "13"},
                          "location": {"start": 32315508, "end": 32400268}, ...}}
        """
        return await op_get_transcript(client, genome_id, stable_id, symbol)

    @mcp.tool(task=TASK)
    async def transcript_search(
        query: str,
        genome_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Search for transcripts by identifier across one or more genomes.

        The query matches transcript identifiers (e.g. a stable id), not free
        text such as gene names.

        Example:
            transcript_search(query="ENST00000380152", per_page=5)
            -> {"meta": {"total_hits": 1, "page": 1, "per_page": 5},
                "matches": [{"stable_id": "ENST00000380152.8",
                             "symbol": "BRCA2-201", ...}]}
        """
        return await op_transcript_search(
            client, query, genome_ids or [HUMAN_GENOME_ID], page, per_page
        )

    @mcp.tool(task=TASK)
    async def get_product_by_id(
        stable_id: str, genome_id: str = HUMAN_GENOME_ID
    ) -> dict[str, Any] | None:
        """Get a protein product by its (versioned) stable id.

        Example:
            get_product_by_id(stable_id="ENSP00000369497.3")
            -> {"stable_id": "ENSP00000369497.3", "type": "Protein",
                "length": 3418, "version": 3}
        """
        return await op_get_product_by_id(client, genome_id, stable_id)

    @mcp.tool(task=TASK)
    async def get_region(
        name: str, genome_id: str = HUMAN_GENOME_ID
    ) -> dict[str, Any] | None:
        """Get a region (e.g. a chromosome ``13``) by name in a genome.

        Example:
            get_region(name="13")
            -> {"name": "13", "length": 114364328, "code": "chromosome",
                "topology": "linear"}
        """
        return await op_get_region(client, genome_id, name)

    @mcp.tool(task=TASK)
    async def overlap_region(
        region_name: str,
        start: int,
        end: int,
        genome_id: str = HUMAN_GENOME_ID,
    ) -> dict[str, Any]:
        """List genes and transcripts overlapping a genomic interval.

        Example:
            overlap_region(region_name="13", start=32315086, end=32400268)
            -> {"genes": [{"symbol": "BRCA2", "stable_id": "ENSG00000139618.18",
                           ...}],
                "transcripts": [{"stable_id": "ENST00000380152.8", ...}, ...]}
        """
        return await op_overlap_region(client, genome_id, region_name, start, end)

    @mcp.tool(task=TASK)
    async def find_genomes(
        scientific_name: str | None = None,
        common_name: str | None = None,
        ensembl_name: str | None = None,
        assembly_accession_id: str | None = None,
        tolid: str | None = None,
        species_taxonomy_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve a species/assembly keyword to genome(s), including genome_id.

        Note: this search can be slow (and occasionally errors) on the Ensembl
        beta server.

        Example:
            find_genomes(scientific_name="Homo sapiens")
            -> [{"genome_id": "3704ceb1-948d-11ec-a39d-005056b38ce3",
                 "assembly_accession": "GCA_000001405.14",
                 "scientific_name": "Homo sapiens", "parlance_name": "Human",
                 "genome_tag": "grch37", "taxon_id": 9606}, ...]
        """
        keyword = GenomeKeywordInput(
            scientific_name=scientific_name,
            common_name=common_name,
            ensembl_name=ensembl_name,
            assembly_accession_id=assembly_accession_id,
            tolid=tolid,
            species_taxonomy_id=species_taxonomy_id,
        )
        return await op_find_genomes(client, keyword)

    @mcp.tool(task=TASK)
    async def get_genome(genome_id: str = HUMAN_GENOME_ID) -> dict[str, Any] | None:
        """Get genome metadata by genome_id.

        Example:
            get_genome(genome_id="a7335667-93e7-11ec-a39d-005056b38ce3")
            -> {"genome_id": "a7335667-93e7-11ec-a39d-005056b38ce3",
                "scientific_name": "Homo sapiens",
                "assembly_accession": "GCA_000001405.29", "is_reference": true}
        """
        return await op_get_genome(client, genome_id)

    @mcp.tool(task=TASK)
    async def graphql_query(
        query: str,
        variables: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> dict[str, Any]:
        """Run an arbitrary GraphQL query against the Ensembl endpoint.

        Example:
            graphql_query(query="{ version { api { major minor patch } } }")
            -> {"version": {"api": {"major": "0", "minor": "2",
                                     "patch": "0-beta"}}}
        """
        return await client.execute(query, variables, endpoint)

    @mcp.tool(task=TASK)
    async def graphql_query_to_file(
        query: str,
        variables: dict[str, Any] | None = None,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Run an arbitrary GraphQL query and write the result to a JSON file.

        Use this instead of ``graphql_query`` when a query may return a large
        payload that would be inconvenient for an LLM context. Files are written
        under the configured ``ENSEMBL_MCP_OUTPUT_DIR`` directory. ``output_name``
        must be a filename, not a path.

        Example:
            graphql_query_to_file(
                query="{ version { api { major minor patch } } }",
                output_name="ensembl_version.json",
            )
            -> {"path": ".ensembl_mcp_outputs/ensembl_version.json",
                "bytes": 89, "keys": ["version"]}
        """
        return await op_graphql_query_to_file(
            client, query, variables, settings.output_dir, output_name
        )

    @mcp.tool(task=TASK)
    async def bulk_find_genes(
        symbols: list[str],
        genome_id: str = HUMAN_GENOME_ID,
        ctx: Context | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Resolve many gene symbols at once (good background task), with progress.

        Returns the resolved genes plus the symbols that could not be found.

        Example:
            bulk_find_genes(symbols=["BRCA2", "TP53", "NOPE"])
            -> {"found": [{"symbol": "BRCA2", ...}, {"symbol": "TP53", ...}],
                "missing": [{"symbol": "NOPE"}]}
        """
        return await op_bulk_find_genes(client, symbols, genome_id, ctx)

    return mcp
