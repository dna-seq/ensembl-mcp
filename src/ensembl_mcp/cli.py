import asyncio
import json
from enum import Enum
from typing import Any

import typer

from ensembl_mcp import server
from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import HUMAN_GENOME_ID, get_settings
from ensembl_mcp.models import GenomeKeywordInput
from ensembl_mcp.server import create_server

app = typer.Typer(
    help="Ensembl beta GraphQL MCP server and live example runner.",
    no_args_is_help=True,
)
examples_app = typer.Typer(
    help="Run real queries against the live Ensembl endpoint for manual testing.",
    no_args_is_help=True,
)
app.add_typer(examples_app, name="examples")


class Transport(str, Enum):
    stdio = "stdio"
    http = "http"


def _print(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


@app.command()
def serve(
    transport: Transport = typer.Option(
        Transport.stdio, help="Transport to serve on."
    ),
    host: str = typer.Option("127.0.0.1", help="Host for the HTTP transport."),
    port: int = typer.Option(8000, help="Port for the HTTP transport."),
) -> None:
    """Run the MCP server over stdio or streamable HTTP."""
    mcp = create_server()
    if transport is Transport.stdio:
        mcp.run()
    else:
        mcp.run(transport="http", host=host, port=port)


@app.command("agent")
def run_agent(
    query: str = typer.Argument(..., help="Natural-language Ensembl question."),
    model_id: str | None = typer.Option(
        None,
        "--model",
        help="Override ENSEMBL_MCP_AGENT_MODEL_ID for this run.",
    ),
) -> None:
    """Answer a natural-language Ensembl query using the optional Agno agent."""
    from ensembl_mcp.agent import get_agent_api_key, run_agent_query

    settings = get_settings()
    if model_id is not None:
        settings = settings.model_copy(update={"agent_model_id": model_id})
    if get_agent_api_key(settings) is None:
        typer.echo(
            "Set ENSEMBL_MCP_AGENT_API_KEY in .env or the environment "
            "to use the agent.",
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(run_agent_query(query, settings))


@examples_app.command("version")
def example_version() -> None:
    """Print the Ensembl GraphQL API version."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_version(client)))


@examples_app.command("variant")
def example_variant(
    identifier: str = typer.Argument(
        ..., help="Bare rsID or region:position:rsid variant id."
    ),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
    compact: bool = typer.Option(False, help="Return a smaller annotation payload."),
) -> None:
    """Resolve and annotate a short variant."""
    settings = get_settings()
    client = EnsemblGraphQLClient(settings)
    if ":" in identifier:
        result = server.op_get_variant(
            client,
            genome_id,
            identifier,
            settings.variation_endpoint,
            not compact,
        )
    else:
        result = server.op_get_variant_by_rsid(
            client,
            identifier,
            genome_id,
            settings.variation_endpoint,
            full=not compact,
        )
    _print(asyncio.run(result))


@examples_app.command("resolve-rsids")
def example_resolve_rsids(
    rsids: list[str] = typer.Argument(..., help="One or more bare rsIDs."),
    species: str = typer.Option("human", help="Legacy REST species name."),
    assembly: str = typer.Option("GRCh38", help="Assembly mapping to retain."),
) -> None:
    """Resolve one or more rsIDs to coordinate identifiers."""
    client = EnsemblGraphQLClient(get_settings())
    _print(
        asyncio.run(
            server.op_batch_resolve_rsids(
                client,
                rsids,
                species,
                assembly,
            )
        )
    )


@examples_app.command("resolve-coordinates")
def example_resolve_coordinates(
    coordinates: list[str] = typer.Argument(
        ..., help="One or more exact region:position coordinates."
    ),
    species: str = typer.Option("human", help="Ensembl REST species name."),
) -> None:
    """Resolve coordinates to overlapping variations."""
    client = EnsemblGraphQLClient(get_settings())
    _print(
        asyncio.run(
            server.op_batch_resolve_coordinates(
                client,
                coordinates,
                species,
            )
        )
    )


@examples_app.command("populations")
def example_populations(
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """List variant-frequency population panels."""
    settings = get_settings()
    client = EnsemblGraphQLClient(settings)
    _print(
        asyncio.run(
            server.op_list_variant_populations(
                client,
                genome_id,
                settings.variation_endpoint,
            )
        )
    )


@examples_app.command("homologies")
def example_homologies(
    gene_stable_id: str = typer.Argument(..., help="Ensembl gene stable ID."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """Retrieve compara homologies for a gene."""
    settings = get_settings()
    client = EnsemblGraphQLClient(settings)
    _print(
        asyncio.run(
            server.op_get_homologies(
                client,
                genome_id,
                gene_stable_id,
                settings.compara_endpoint,
            )
        )
    )


@examples_app.command("releases")
def example_releases() -> None:
    """Print Ensembl beta release metadata."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_get_releases(client)))


@examples_app.command("gene")
def example_gene(
    symbol: str = typer.Argument(..., help="Gene symbol, e.g. BRCA2."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """Find genes by symbol."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_find_genes_by_symbol(client, symbol, genome_id)))


@examples_app.command("transcript")
def example_transcript(
    stable_id: str = typer.Argument(..., help="Transcript stable id."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """Get a transcript by stable id."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_get_transcript(client, genome_id, stable_id, None)))


@examples_app.command("region")
def example_region(
    name: str = typer.Argument(..., help="Region name, e.g. 13."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """Get a region by name."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_get_region(client, genome_id, name)))


@examples_app.command("overlap")
def example_overlap(
    region_name: str = typer.Argument(..., help="Region name, e.g. 13."),
    start: int = typer.Argument(..., help="Start coordinate."),
    end: int = typer.Argument(..., help="End coordinate."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """List genes/transcripts overlapping a genomic interval."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_overlap_region(client, genome_id, region_name, start, end)))


@examples_app.command("genome")
def example_genome(
    scientific_name: str | None = typer.Option(None, help="Scientific name keyword."),
    common_name: str | None = typer.Option(None, help="Common name keyword."),
    genome_id: str | None = typer.Option(None, help="Look up a genome by its id instead."),
) -> None:
    """Resolve a species keyword to genome(s), or fetch a genome by id."""
    client = EnsemblGraphQLClient(get_settings())
    if genome_id is not None:
        _print(asyncio.run(server.op_get_genome(client, genome_id)))
        return
    keyword = GenomeKeywordInput(scientific_name=scientific_name, common_name=common_name)
    _print(asyncio.run(server.op_find_genomes(client, keyword)))


@examples_app.command("search")
def example_search(
    query: str = typer.Argument(..., help="Search query."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
    per_page: int = typer.Option(5, help="Results per page."),
) -> None:
    """Full-text transcript search."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_transcript_search(client, query, [genome_id], 1, per_page)))


@examples_app.command("bulk")
def example_bulk(
    symbols: list[str] = typer.Argument(..., help="Gene symbols to resolve."),
    genome_id: str = typer.Option(HUMAN_GENOME_ID, help="Genome id (UUID)."),
) -> None:
    """Resolve many gene symbols at once (the background-task showcase)."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_bulk_find_genes(client, symbols, genome_id, None)))


@examples_app.command("sequence")
def example_sequence(
    sequence_id: str = typer.Argument(..., help="Refget sequence digest id."),
    start: int | None = typer.Option(None, help="0-indexed inclusive start offset."),
    end: int | None = typer.Option(None, help="0-indexed exclusive end offset."),
    output_name: str | None = typer.Option(
        None,
        help="Write sequence under ENSEMBL_MCP_OUTPUT_DIR with this filename.",
    ),
) -> None:
    """Retrieve a Refget sequence or subsequence, optionally as a file."""
    settings = get_settings()
    client = EnsemblGraphQLClient(settings)
    if output_name is not None:
        _print(
            asyncio.run(
                server.op_get_sequence_to_file(
                    client, sequence_id, settings.output_dir, start, end, output_name
                )
            )
        )
        return
    typer.echo(asyncio.run(server.op_get_sequence(client, sequence_id, start, end)))


@examples_app.command("sequence-metadata")
def example_sequence_metadata(
    sequence_id: str = typer.Argument(..., help="Refget sequence digest id."),
) -> None:
    """Retrieve Refget metadata for a sequence digest id."""
    client = EnsemblGraphQLClient(get_settings())
    _print(asyncio.run(server.op_get_sequence_metadata(client, sequence_id)))


@examples_app.command("raw")
def example_raw(
    query: str = typer.Argument(..., help="A raw GraphQL query string."),
    output_name: str | None = typer.Option(
        None,
        help="Write the JSON result under ENSEMBL_MCP_OUTPUT_DIR with this filename.",
    ),
) -> None:
    """Run a raw GraphQL query, optionally writing the result to a file."""
    settings = get_settings()
    client = EnsemblGraphQLClient(settings)
    if output_name is not None:
        _print(
            asyncio.run(
                server.op_graphql_query_to_file(
                    client, query, None, settings.output_dir, output_name
                )
            )
        )
        return
    _print(asyncio.run(client.execute(query)))


if __name__ == "__main__":
    app()
