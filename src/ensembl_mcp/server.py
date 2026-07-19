import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from eliot import start_action
from fastmcp import Context, FastMCP
from fastmcp.utilities.tasks import TaskConfig
from mcp.types import ToolAnnotations

from ensembl_mcp import backend_queries, queries
from ensembl_mcp.client import EnsemblGraphQLClient, GraphQLError
from ensembl_mcp.config import HUMAN_GENOME_ID, Settings, get_settings
from ensembl_mcp.models import (
    BatchVariantLookupResult,
    GenomeKeywordInput,
    RsidMapping,
    RsidResolution,
    VariantAnnotation,
    VariantLookupResult,
    normalize_coordinate,
    normalize_rsid,
)

# Every data tool may run synchronously or be promoted to a background task by
# the client (the MCP background-task protocol, SEP-1686).
TASK = TaskConfig(mode="optional")
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
LOCAL_WRITE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


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


async def op_variation_version(
    client: EnsemblGraphQLClient, variation_endpoint: str
) -> dict[str, Any]:
    data = await client.execute(
        backend_queries.VARIATION_VERSION_QUERY,
        endpoint=variation_endpoint,
    )
    return data["version"]


async def op_get_variant(
    client: EnsemblGraphQLClient,
    genome_id: str,
    variant_id: str,
    variation_endpoint: str,
    full: bool = True,
) -> dict[str, Any] | None:
    query = (
        backend_queries.VARIANT_QUERY
        if full
        else backend_queries.COMPACT_VARIANT_QUERY
    )
    data = await client.execute(
        query,
        {"genome_id": genome_id, "variant_id": variant_id},
        variation_endpoint,
    )
    return data.get("variant")


async def op_list_variant_populations(
    client: EnsemblGraphQLClient,
    genome_id: str,
    variation_endpoint: str,
) -> list[dict[str, Any]]:
    data = await client.execute(
        backend_queries.POPULATIONS_QUERY,
        {"genome_id": genome_id},
        variation_endpoint,
    )
    return [
        population
        for population in data.get("populations") or []
        if population is not None
    ]


async def op_resolve_rsid(
    client: EnsemblGraphQLClient,
    rsid: str,
    species: str = "human",
    assembly: str = "GRCh38",
) -> dict[str, Any]:
    normalized = normalize_rsid(rsid)
    data = await client.fetch_rsid(species, normalized)
    mappings = [
        RsidMapping.model_validate(mapping)
        for mapping in data.get("mappings") or []
        if mapping.get("assembly_name") == assembly
    ]
    resolution = RsidResolution(
        rsid=normalized,
        species=species,
        assembly=assembly,
        mappings=mappings,
        variant_ids=[mapping.variant_id(normalized) for mapping in mappings],
    )
    return resolution.model_dump()


async def op_batch_resolve_rsids(
    client: EnsemblGraphQLClient,
    rsids: list[str],
    species: str = "human",
    assembly: str = "GRCh38",
    ctx: Context | None = None,
) -> dict[str, list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    total = len(rsids)
    with start_action(
        action_type="batch_resolve_rsids",
        count=total,
        species=species,
        assembly=assembly,
    ):
        for index, rsid in enumerate(rsids, start=1):
            try:
                result = await op_resolve_rsid(client, rsid, species, assembly)
                if result["mappings"]:
                    resolved.append(result)
                else:
                    missing.append({"rsid": rsid, "reason": "No mapping for assembly"})
            except (ValueError, httpx.HTTPStatusError) as error:
                missing.append({"rsid": rsid, "reason": str(error)})
            if ctx is not None:
                await ctx.report_progress(
                    progress=index,
                    total=total,
                    message=f"Resolved {rsid}",
                )
    return {"resolved": resolved, "missing": missing}


async def op_batch_resolve_coordinates(
    client: EnsemblGraphQLClient,
    coordinates: list[str],
    species: str = "human",
    ctx: Context | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Resolve exact coordinates to every overlapping variation."""
    found: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    total = len(coordinates)
    with start_action(
        action_type="batch_resolve_coordinates",
        count=total,
        species=species,
    ):
        for index, coordinate in enumerate(coordinates, start=1):
            try:
                normalized = normalize_coordinate(coordinate)
                variations = await client.fetch_variations_at_coordinate(species, normalized)
                if variations:
                    found.append({"coordinate": normalized, "variations": variations})
                else:
                    missing.append({"coordinate": coordinate, "reason": "No variations found"})
            except (ValueError, httpx.HTTPStatusError) as error:
                missing.append({"coordinate": coordinate, "reason": str(error)})
            if ctx is not None:
                await ctx.report_progress(
                    progress=index,
                    total=total,
                    message=f"Resolved {coordinate}",
                )
    return {"found": found, "missing": missing}


async def op_get_variant_by_rsid(
    client: EnsemblGraphQLClient,
    rsid: str,
    genome_id: str,
    variation_endpoint: str,
    species: str = "human",
    assembly: str = "GRCh38",
    full: bool = True,
) -> dict[str, Any]:
    resolution = await op_resolve_rsid(client, rsid, species, assembly)
    variants = [
        variant
        for variant_id in resolution["variant_ids"]
        if (
            variant := await op_get_variant(
                client,
                genome_id,
                variant_id,
                variation_endpoint,
                full,
            )
        )
        is not None
    ]
    return {"resolution": resolution, "variants": variants}


async def op_batch_get_variants_by_rsid(
    client: EnsemblGraphQLClient,
    rsids: list[str],
    genome_id: str,
    variation_endpoint: str,
    species: str = "human",
    assembly: str = "GRCh38",
    ctx: Context | None = None,
) -> dict[str, list[dict[str, Any]]]:
    found: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    total = len(rsids)
    with start_action(
        action_type="batch_get_variants_by_rsid",
        count=total,
        genome_id=genome_id,
    ):
        for index, rsid in enumerate(rsids, start=1):
            try:
                result = await op_get_variant_by_rsid(
                    client,
                    rsid,
                    genome_id,
                    variation_endpoint,
                    species,
                    assembly,
                    full=False,
                )
                if result["variants"]:
                    found.append(result)
                else:
                    missing.append({"rsid": rsid, "reason": "No variant found"})
            except (ValueError, httpx.HTTPStatusError, GraphQLError) as error:
                missing.append({"rsid": rsid, "reason": str(error)})
            if ctx is not None:
                await ctx.report_progress(
                    progress=index,
                    total=total,
                    message=f"Annotated {rsid}",
                )
    return {"found": found, "missing": missing}


async def op_get_homologies(
    client: EnsemblGraphQLClient,
    genome_id: str,
    gene_stable_id: str,
    compara_endpoint: str,
) -> list[dict[str, Any]]:
    data = await client.execute(
        backend_queries.HOMOLOGIES_QUERY,
        {"genome_id": genome_id, "gene_stable_id": gene_stable_id},
        compara_endpoint,
    )
    return data.get("homologies") or []


async def op_get_releases(client: EnsemblGraphQLClient) -> Any:
    return await client.fetch_releases()


async def op_get_variants_in_region(
    client: EnsemblGraphQLClient,
    region_name: str,
    start: int,
    end: int,
    species: str = "human",
) -> dict[str, Any]:
    """Retrieve all known short variants overlapping a genomic interval."""
    variants = await client.fetch_variations_in_region(
        species, region_name, start, end
    )
    return {
        "region": region_name,
        "start": start,
        "end": end,
        "total": len(variants),
        "variants": variants,
    }


async def op_get_gene_phenotypes(
    client: EnsemblGraphQLClient,
    gene: str,
    species: str = "human",
) -> dict[str, Any]:
    """Retrieve phenotype/disease associations for a gene."""
    phenotypes = await client.fetch_phenotypes_for_gene(species, gene)
    return {
        "gene": gene,
        "total": len(phenotypes),
        "phenotypes": phenotypes,
    }


async def op_variant_recoder(
    client: EnsemblGraphQLClient,
    variant_id: str,
    species: str = "human",
) -> list[dict[str, Any]]:
    """Convert a variant between rsID, HGVS, SPDI, and VCF representations."""
    return await client.fetch_variant_recoder(species, variant_id)


async def op_get_protein_sequence(
    client: EnsemblGraphQLClient,
    genome_id: str,
    gene_symbol: str | None = None,
    product_stable_id: str | None = None,
) -> dict[str, Any]:
    """Get protein sequence via gene symbol or product ID, bridging to Refget."""
    if product_stable_id:
        product = await client.execute(
            queries.PRODUCT_BY_ID_QUERY,
            {"genome_id": genome_id, "stable_id": product_stable_id},
        )
        prod = product.get("product")
        if not prod:
            return {"error": f"Product {product_stable_id} not found"}
        checksum = prod["sequence"]["checksum"]
        length = prod["length"]
        seq = await client.fetch_sequence(checksum)
        return {
            "product_stable_id": prod["stable_id"],
            "length": length,
            "checksum": checksum,
            "sequence": seq,
        }

    if gene_symbol:
        genes = await op_find_genes_by_symbol(client, gene_symbol, genome_id)
        if not genes:
            return {"error": f"Gene {gene_symbol!r} not found"}
        gene = genes[0]
        transcripts = gene.get("transcripts") or []
        canonical = next(
            (
                tx
                for tx in transcripts
                if (tx.get("metadata") or {}).get("canonical", {}).get("value")
            ),
            transcripts[0] if transcripts else None,
        )
        if not canonical:
            return {"error": f"No transcripts found for {gene_symbol}"}
        tx = await client.execute(
            queries.TRANSCRIPT_BY_ID_QUERY,
            {"genome_id": genome_id, "stable_id": canonical["stable_id"]},
        )
        transcript = tx.get("transcript")
        if not transcript:
            return {"error": f"Transcript {canonical['stable_id']} not found"}
        pgcs = transcript.get("product_generating_contexts") or []
        prod_ctx = next((p for p in pgcs if p.get("product")), None)
        if not prod_ctx or not prod_ctx["product"]:
            return {"error": f"No protein product for transcript {canonical['stable_id']}"}
        prod = prod_ctx["product"]
        checksum = prod["sequence"]["checksum"]
        seq = await client.fetch_sequence(checksum)
        mane = (canonical.get("metadata") or {}).get("mane")
        return {
            "gene_symbol": gene_symbol,
            "transcript_stable_id": canonical["stable_id"],
            "transcript_symbol": canonical.get("symbol"),
            "is_canonical": True,
            "mane": mane,
            "product_stable_id": prod["stable_id"],
            "length": prod["length"],
            "checksum": checksum,
            "sequence": seq,
        }

    raise ValueError("Provide either gene_symbol or product_stable_id.")


def _build_clinical_summary(
    variant: dict[str, Any],
    populations: list[str] | None = None,
) -> dict[str, Any]:
    """Distill a full variant annotation into a clinical-friendly summary."""
    default_pops = {"gnomADe:ALL", "gnomADg:ALL", "1000GENOMES:phase_3:ALL"}
    target_pops = set(populations) if populations else default_pops

    summary: dict[str, Any] = {
        "name": variant.get("name"),
        "type": variant.get("type"),
        "allele_type": (variant.get("allele_type") or {}).get("value"),
        "location": None,
        "alleles": [],
        "variant_predictions": [],
    }

    s = variant.get("slice") or {}
    loc = s.get("location") or {}
    region = (s.get("region") or {}).get("name")
    if region and loc.get("start"):
        summary["location"] = {
            "region": region,
            "start": loc["start"],
            "end": loc.get("end"),
        }

    for pr in variant.get("prediction_results") or []:
        method = pr.get("analysis_method") or {}
        entry: dict[str, Any] = {
            "tool": method.get("tool"),
            "score": pr.get("score"),
            "result": pr.get("result"),
        }
        qual = method.get("qualifier")
        if qual:
            entry["qualifier"] = qual.get("result_type")
        classification = pr.get("classification")
        if classification and classification.get("value"):
            entry["classification"] = classification["value"]
        summary["variant_predictions"].append(entry)

    for allele in variant.get("alleles") or []:
        allele_summary: dict[str, Any] = {
            "name": allele.get("name"),
            "allele_sequence": allele.get("allele_sequence"),
            "reference_sequence": allele.get("reference_sequence"),
            "allele_type": (allele.get("allele_type") or {}).get("value"),
        }

        filtered_freqs = [
            {
                "population": f["population_name"],
                "frequency": f.get("allele_frequency"),
                "is_minor": f.get("is_minor_allele"),
            }
            for f in allele.get("population_frequencies") or []
            if f["population_name"] in target_pops
        ]
        allele_summary["frequencies"] = filtered_freqs

        allele_preds = []
        for pr in allele.get("prediction_results") or []:
            method = pr.get("analysis_method") or {}
            entry = {
                "tool": method.get("tool"),
                "score": pr.get("score"),
            }
            qual = method.get("qualifier")
            if qual:
                entry["qualifier"] = qual.get("result_type")
            allele_preds.append(entry)
        allele_summary["predictions"] = allele_preds

        phenotypes = []
        for pa in allele.get("phenotype_assertions") or []:
            phenotype = pa.get("phenotype") or {}
            phenotypes.append({
                "name": phenotype.get("name"),
                "source": (phenotype.get("source") or {}).get("name"),
            })
        if phenotypes:
            allele_summary["phenotypes"] = phenotypes

        consequences = []
        for mc in allele.get("predicted_molecular_consequences") or []:
            cons_terms = [c.get("value") for c in mc.get("consequences") or []]
            mc_preds = {}
            max_splice_delta = None
            for pr in mc.get("prediction_results") or []:
                method = pr.get("analysis_method") or {}
                tool = method.get("tool", "")
                qual = method.get("qualifier") or {}
                result_type = qual.get("result_type", "")
                if tool == "SIFT":
                    mc_preds["sift_score"] = pr.get("score")
                    cls = pr.get("classification")
                    if cls:
                        mc_preds["sift_classification"] = cls.get("value")
                elif tool == "PolyPhen":
                    mc_preds["polyphen_score"] = pr.get("score")
                    cls = pr.get("classification")
                    if cls:
                        mc_preds["polyphen_classification"] = cls.get("value")
                elif tool == "SpliceAI" and "Delta score" in result_type:
                    score = pr.get("score")
                    if score is not None:
                        if max_splice_delta is None or abs(score) > abs(max_splice_delta):
                            max_splice_delta = score
            if max_splice_delta is not None:
                mc_preds["spliceai_max_delta"] = max_splice_delta

            consequence_entry: dict[str, Any] = {
                "gene_symbol": mc.get("gene_symbol"),
                "transcript": mc.get("stable_id"),
                "consequences": cons_terms,
                "protein_position": (mc.get("protein_location") or {}).get("start"),
                "cds_position": (mc.get("cds_location") or {}).get("start"),
            }
            consequence_entry.update(mc_preds)
            consequences.append(consequence_entry)
        if consequences:
            allele_summary["consequences"] = consequences

        summary["alleles"].append(allele_summary)

    return summary


def _default_graphql_output_name(
    query: str, variables: dict[str, Any] | None = None
) -> str:
    payload = json.dumps({"query": query, "variables": variables or {}}, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"ensembl_graphql_{timestamp}_{digest}.json"


def _default_variant_output_name(variant_id: str) -> str:
    digest = hashlib.sha256(variant_id.encode("utf-8")).hexdigest()[:12]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"ensembl_variant_{timestamp}_{digest}.json"


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


async def op_get_variant_to_file(
    client: EnsemblGraphQLClient,
    genome_id: str,
    variant_id: str,
    variation_endpoint: str,
    output_dir: str,
    output_name: str | None = None,
) -> dict[str, Any]:
    output_path = _resolve_output_path(
        output_dir,
        output_name,
        _default_variant_output_name(variant_id),
        ".json",
    )
    variant = await op_get_variant(
        client,
        genome_id,
        variant_id,
        variation_endpoint,
        full=True,
    )
    encoded = json.dumps(variant, indent=2, ensure_ascii=False).encode("utf-8")
    output_path.write_bytes(encoded)
    return {
        "path": str(output_path),
        "bytes": len(encoded),
        "variant_id": variant_id,
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
            "Query Ensembl beta for genes, transcripts, proteins, regions, genomes, "
            "short variants, populations, homologies, releases, and GA4GH Refget "
            "sequences. Use resolve_rsid or get_variant_by_rsid for bare rsIDs; the "
            "variation GraphQL backend itself requires region:position:rsid. Most "
            "lookups need a genome_id (a UUID); use find_genomes to resolve species. "
            f"The human reference genome_id is {settings.human_genome_id}."
        ),
    )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_version() -> dict[str, Any]:
        """Return the Ensembl GraphQL API version.

        Example:
            get_version()
            -> {"api": {"major": "0", "minor": "2", "patch": "0-beta"}}
        """
        return await op_version(client)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_variation_version() -> dict[str, Any]:
        """Return the Ensembl variation GraphQL API version."""
        return await op_variation_version(client, settings.variation_endpoint)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_variant(
        variant_id: str,
        genome_id: str = HUMAN_GENOME_ID,
        full: bool = True,
    ) -> VariantAnnotation | None:
        """Get a short variant by ``region:position:rsid`` coordinate identifier.

        Read the typed result as follows: ``slice`` gives region/location/strand;
        each ``alleles[]`` item gives reference and alternate sequence plus
        ``population_frequencies[]`` (always cite ``population_name``).
        With ``full=True``, each allele also has ``phenotype_assertions[]`` and
        transcript-level ``predicted_molecular_consequences[]`` with gene,
        transcript, protein, SO consequence, and cDNA/CDS/protein coordinates.

        Prediction scope matters: variant ``prediction_results`` contain Ensembl
        VEP, GERP, and AncestralAllele; allele results contain CADD; molecular
        consequence results contain SIFT, SpliceAI, and currently PolyPhen.
        Scores from different methods are not interchangeable.

        Example: ``1:230710048:rs699`` returns chromosome 1 position 230710048,
        A reference/G alternate, AGT transcript consequences, and population
        records such as ``gnomADe:ALL``. Use ``full=False`` to omit phenotypes
        and molecular consequences, or ``get_variant_to_file`` for a large result.
        """
        result = await op_get_variant(
            client,
            genome_id,
            variant_id,
            settings.variation_endpoint,
            full,
        )
        return VariantAnnotation.model_validate(result) if result is not None else None

    @mcp.tool(task=TASK, annotations=LOCAL_WRITE)
    async def get_variant_to_file(
        variant_id: str,
        genome_id: str = HUMAN_GENOME_ID,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Write the full ``VariantAnnotation`` payload to JSON under the output directory."""
        return await op_get_variant_to_file(
            client,
            genome_id,
            variant_id,
            settings.variation_endpoint,
            settings.output_dir,
            output_name,
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def list_variant_populations(
        genome_id: str = HUMAN_GENOME_ID,
    ) -> list[dict[str, Any]]:
        """List population panels available for variant frequencies in a genome."""
        return await op_list_variant_populations(
            client,
            genome_id,
            settings.variation_endpoint,
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def resolve_rsid(
        rsid: str,
        species: str = "human",
        assembly: str = "GRCh38",
    ) -> dict[str, Any]:
        """Resolve a bare rsID to every matching coordinate ID for an assembly."""
        return await op_resolve_rsid(client, rsid, species, assembly)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def batch_resolve_rsids(
        rsids: list[str],
        species: str = "human",
        assembly: str = "GRCh38",
        ctx: Context | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Resolve many bare rsIDs, preserving resolved and missing outcomes."""
        return await op_batch_resolve_rsids(
            client,
            rsids,
            species,
            assembly,
            ctx,
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def batch_resolve_coordinates(
        coordinates: list[str],
        species: str = "human",
        ctx: Context | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Resolve exact ``region:position`` coordinates to all overlapping variations.

        Each result includes the overlapping variation IDs (such as rsIDs), alleles,
        consequence type, and assembly. Coordinates are interpreted as 1-based,
        inclusive Ensembl coordinates; ``chr1:230710048`` is also accepted.
        """
        return await op_batch_resolve_coordinates(client, coordinates, species, ctx)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_variant_by_rsid(
        rsid: str,
        genome_id: str = HUMAN_GENOME_ID,
        species: str = "human",
        assembly: str = "GRCh38",
        full: bool = True,
    ) -> VariantLookupResult:
        """Resolve a bare rsID and annotate every matching assembly coordinate.

        ``resolution.mappings`` contains the exact assembly coordinates and
        alleles returned by Ensembl REST; ``resolution.variant_ids`` contains the
        coordinate IDs queried against variation GraphQL. Read each item in
        ``variants`` using the same typed allele, frequency, phenotype,
        consequence, and prediction structure documented by ``get_variant``.

        Example: ``rs699`` resolves to ``1:230710048:rs699`` on GRCh38. Do not
        silently discard additional mappings when ``variants`` has multiple items.
        """
        return VariantLookupResult.model_validate(
            await op_get_variant_by_rsid(
                client,
                rsid,
                genome_id,
                settings.variation_endpoint,
                species,
                assembly,
                full,
            )
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def batch_get_variants_by_rsid(
        rsids: list[str],
        genome_id: str = HUMAN_GENOME_ID,
        species: str = "human",
        assembly: str = "GRCh38",
        ctx: Context | None = None,
    ) -> BatchVariantLookupResult:
        """Resolve and compactly annotate many rsIDs with per-item outcomes.

        ``found`` contains ``VariantLookupResult`` items and ``missing`` preserves
        each unresolved rsID and reason. Compact variants retain identity, locus,
        alleles, frequencies, display summaries, and variant/allele predictions;
        phenotype assertions and transcript molecular consequences are omitted.
        """
        return BatchVariantLookupResult.model_validate(
            await op_batch_get_variants_by_rsid(
                client,
                rsids,
                genome_id,
                settings.variation_endpoint,
                species,
                assembly,
                ctx,
            )
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_homologies(
        gene_stable_id: str,
        genome_id: str = HUMAN_GENOME_ID,
    ) -> list[dict[str, Any]]:
        """Return compara homologies for an Ensembl gene stable ID.

        The live beta backend currently returns an empty list for known human
        genes while its data load is incomplete.
        """
        return await op_get_homologies(
            client,
            genome_id,
            gene_stable_id,
            settings.compara_endpoint,
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_releases() -> Any:
        """Return integrated and partial release metadata from Ensembl beta."""
        return await op_get_releases(client)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=LOCAL_WRITE)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_sequence_metadata(sequence_id: str) -> dict[str, Any]:
        """Retrieve metadata and cross-authority aliases for a sequence digest ID.

        Example:
            get_sequence_metadata(sequence_id="6681ac2f62509cfc220d78751b8dc524")
            -> {"metadata": {"length": 12345, "aliases": [{"naming_authority": "ensembl", "alias": "..."}]}}
        """
        return await op_get_sequence_metadata(client, sequence_id)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def find_genes_by_symbol(
        symbol: str, genome_id: str = HUMAN_GENOME_ID
    ) -> list[dict[str, Any]]:
        """Find genes by their display symbol (e.g. ``BRCA2``) in a genome.

        Returns gene metadata including HGNC accession, biotype, alternative
        symbols, cross-references (UniProt, RefSeq, OMIM, Expression Atlas,
        etc.), and a list of all transcripts with MANE Select/canonical flags.

        Example:
            find_genes_by_symbol(symbol="BRCA2")
            -> [{"stable_id": "ENSG00000139618.18", "symbol": "BRCA2",
                 "name": "BRCA2 DNA repair associated", "so_term": "protein_coding",
                 "transcript_count": 15,
                 "metadata": {"name": {"accession_id": "HGNC:1101", ...},
                              "biotype": {"value": "protein_coding"}},
                 "external_references": [...],
                 "alternative_symbols": ["BRCC2", "FANCD1", ...],
                 "transcripts": [{"stable_id": "...", "symbol": "BRCA2-201",
                                  "metadata": {"mane": {"value": "select", ...},
                                               "canonical": {"value": true}}}],
                 "slice": {"region": {"name": "13"}, ...}}]
        """
        return await op_find_genes_by_symbol(client, symbol, genome_id)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_transcript(
        stable_id: str | None = None,
        symbol: str | None = None,
        genome_id: str = HUMAN_GENOME_ID,
    ) -> dict[str, Any] | None:
        """Get a transcript by stable id or symbol (provide one of them).

        Returns full transcript structure including MANE Select/Plus Clinical
        designation, Ensembl canonical flag, APPRIS, TSL level, exon
        coordinates (``spliced_exons``), CDS/UTR boundaries, linked protein
        product with Refget checksum, and cross-references.

        Example:
            get_transcript(stable_id="ENST00000380152")
            -> {"stable_id": "ENST00000380152.8", "symbol": "BRCA2-201",
                "so_term": "protein_coding",
                "metadata": {"mane": {"value": "select", "label": "MANE Select",
                              "ncbi_transcript": {"id": "NM_000059.4", ...}},
                             "canonical": {"value": true, ...},
                             "appris": {"value": "principal2", ...}},
                "spliced_exons": [{"index": 1, "exon": {"stable_id": "...",
                  "slice": {"location": {"start": 32315508, ...}}}, ...}],
                "product_generating_contexts": [{"cds": {"protein_length": 3418},
                  "product": {"stable_id": "ENSP00000369497.3",
                              "sequence": {"checksum": "92addb..."}}}],
                "external_references": [...]}
        """
        return await op_get_transcript(client, genome_id, stable_id, symbol)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_product_by_id(
        stable_id: str, genome_id: str = HUMAN_GENOME_ID
    ) -> dict[str, Any] | None:
        """Get a protein product by its (versioned) stable id.

        Returns protein metadata, domain annotations (``family_matches`` from
        Pfam, PANTHER, etc. with positions and e-values), cross-references
        (PDB structures, Reactome pathways, UniProt, BioGRID, Human Protein
        Atlas), and the Refget sequence checksum. Use the checksum with
        ``get_sequence`` to retrieve the amino acid sequence.

        Example:
            get_product_by_id(stable_id="ENSP00000369497.3")
            -> {"stable_id": "ENSP00000369497.3", "type": "Protein",
                "length": 3418, "version": 3,
                "sequence": {"checksum": "92addb948c6c652abc1dcecca05f26c0",
                             "alphabet": {"value": "amino_acid_alphabet"}},
                "family_matches": [{"sequence_family": {"source": {"name": "Pfam"},
                  "accession_id": "PF00634", "description": "BRCA2"},
                  "relative_location": {"start": 1005, "end": 1033},
                  "evalue": 8.7e-66}, ...],
                "external_references": [{"accession_id": "P51587",
                  "source": {"name": "UniProt/SWISSPROT"}, ...}, ...]}
        """
        return await op_get_product_by_id(client, genome_id, stable_id)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_genome(genome_id: str = HUMAN_GENOME_ID) -> dict[str, Any] | None:
        """Get genome metadata by genome_id.

        Example:
            get_genome(genome_id="a7335667-93e7-11ec-a39d-005056b38ce3")
            -> {"genome_id": "a7335667-93e7-11ec-a39d-005056b38ce3",
                "scientific_name": "Homo sapiens",
                "assembly_accession": "GCA_000001405.29", "is_reference": true}
        """
        return await op_get_genome(client, genome_id)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=LOCAL_WRITE)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
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

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_variants_in_region(
        region_name: str,
        start: int,
        end: int,
        species: str = "human",
    ) -> dict[str, Any]:
        """List all known short variants overlapping a genomic interval.

        Returns rsIDs, alleles, consequence types, clinical significance, and
        source for every catalogued variant in the region. Use with gene
        coordinates from ``find_genes_by_symbol`` to answer "what variants are
        in gene X?".

        The interval uses 1-based inclusive Ensembl coordinates. Large
        intervals (>1 Mb) may return thousands of variants.

        Example:
            get_variants_in_region(region_name="17", start=7661779, end=7687550)
            -> {"region": "17", "start": 7661779, "end": 7687550,
                "total": 12813,
                "variants": [{"id": "rs28934578", "start": 7675088,
                  "consequence_type": "missense_variant",
                  "clinical_significance": ["pathogenic"], ...}, ...]}
        """
        return await op_get_variants_in_region(
            client, region_name, start, end, species
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_gene_phenotypes(
        gene: str,
        species: str = "human",
    ) -> dict[str, Any]:
        """Retrieve phenotype and disease associations for a gene.

        Accepts a gene symbol (e.g. ``TP53``) or Ensembl gene ID. Returns
        associations from ClinVar, Cancer Gene Census, GWAS catalog, OMIM,
        and other sources with PubMed references when available.

        Example:
            get_gene_phenotypes(gene="TP53")
            -> {"gene": "TP53", "total": 443,
                "phenotypes": [{"description": "Li-Fraumeni Syndrome",
                  "source": "ClinVar", "Gene": "ENSG00000141510", ...}, ...]}
        """
        return await op_get_gene_phenotypes(client, gene, species)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def variant_recoder(
        variant_id: str,
        species: str = "human",
    ) -> list[dict[str, Any]]:
        """Convert a variant between rsID, HGVS, SPDI, and VCF representations.

        Input can be an rsID (``rs699``), HGVS notation
        (``ENST00000366667.6:c.776T>C``), or SPDI. Returns all equivalent
        representations including genomic/coding/protein HGVS, SPDI, and
        variant IDs.

        Example:
            variant_recoder(variant_id="rs699")
            -> [{"G": {"hgvsc": ["ENST00000366667.6:c.776T>C", ...],
                        "hgvsp": ["ENSP00000355627.5:p.Met259Thr", ...],
                        "spdi": ["1:230710047:A:G"],
                        "id": ["rs699"]}}]
        """
        return await op_variant_recoder(client, variant_id, species)

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_protein_sequence(
        gene_symbol: str | None = None,
        product_stable_id: str | None = None,
        genome_id: str = HUMAN_GENOME_ID,
    ) -> dict[str, Any]:
        """Retrieve the amino acid sequence for a gene or protein product.

        Bridges core GraphQL to Refget: resolves the gene to its canonical
        transcript, finds the protein product and its Refget checksum, then
        fetches the sequence. Provide either ``gene_symbol`` or
        ``product_stable_id`` (not both needed).

        Example:
            get_protein_sequence(gene_symbol="BRCA2")
            -> {"gene_symbol": "BRCA2",
                "transcript_stable_id": "ENST00000380152.8",
                "is_canonical": true,
                "mane": {"value": "select", "label": "MANE Select", ...},
                "product_stable_id": "ENSP00000369497.3",
                "length": 3418,
                "sequence": "MPIGSKERPT..."}
        """
        return await op_get_protein_sequence(
            client, genome_id, gene_symbol, product_stable_id
        )

    @mcp.tool(task=TASK, annotations=READ_ONLY)
    async def get_variant_clinical_summary(
        rsid: str,
        genome_id: str = HUMAN_GENOME_ID,
        species: str = "human",
        assembly: str = "GRCh38",
        populations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return a compact clinical summary for a variant by rsID.

        Resolves the rsID, fetches the full annotation, and distills it into:
        variant-level predictions (VEP, GERP, AncestralAllele), per-allele
        CADD scores, per-allele population frequencies (filtered to major
        panels: gnomADe:ALL, gnomADg:ALL, 1000GENOMES by default or custom
        ``populations``), phenotype associations, and per-consequence SIFT,
        PolyPhen, and max SpliceAI delta scores.

        Use ``populations`` to request specific panels, e.g.
        ``["gnomADe:afr", "gnomADe:nfe"]``.

        Example:
            get_variant_clinical_summary(rsid="rs28934578")
            -> {"name": "rs28934578", "type": "...",
                "alleles": [{"allele_sequence": "T",
                  "frequencies": [{"population": "gnomADe:ALL",
                                   "frequency": 2.4e-05}],
                  "predictions": [{"tool": "CADD", "score": 28.0}],
                  "phenotypes": [{"name": "Li-Fraumeni syndrome",
                                  "source": "ClinVar"}],
                  "consequences": [{"gene_symbol": "TP53",
                    "consequences": ["missense_variant"],
                    "sift_score": 0.0, "spliceai_max_delta": 0.01,
                    "protein_position": 175}]}]}
        """
        result = await op_get_variant_by_rsid(
            client,
            rsid,
            genome_id,
            settings.variation_endpoint,
            species,
            assembly,
            full=True,
        )
        summaries = [
            _build_clinical_summary(variant, populations)
            for variant in result["variants"]
        ]
        return {
            "resolution": result["resolution"],
            "summaries": summaries,
        }

    return mcp
