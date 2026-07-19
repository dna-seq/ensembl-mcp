import asyncio
from typing import Any

from ensembl_mcp import server
from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import Settings, get_settings
from ensembl_mcp.models import GenomeKeywordInput


def _load_agent() -> type[Any]:
    try:
        from agno.agent import Agent
    except ImportError as error:
        raise RuntimeError(
            "The natural-language agent requires dev dependencies. "
            "Install them with `uv sync --dev`."
        ) from error
    return Agent


def get_agent_api_key(settings: Settings) -> str | None:
    """Return the configured model API key."""
    explicit_key = (settings.agent_api_key or "").strip()
    if explicit_key:
        return explicit_key
    return None


def _create_model(settings: Settings, api_key: str) -> Any:
    try:
        from agno.models.openai import OpenAIChat

        return OpenAIChat(
            id=settings.agent_model_id,
            api_key=api_key,
            base_url=settings.agent_base_url or None,
            timeout=settings.agent_timeout,
        )
    except ImportError as error:
        raise RuntimeError(
            "The configured agent model requires missing dev dependencies. "
            "Install them with `uv sync --dev`."
        ) from error


def create_agent(settings: Settings | None = None) -> Any:
    """Create an Agno agent that answers natural-language Ensembl questions."""
    settings = settings or get_settings()
    api_key = get_agent_api_key(settings)
    if not api_key:
        raise ValueError(
            "Set ENSEMBL_MCP_AGENT_API_KEY in .env or the environment "
            "to use the agent."
        )

    agent_cls = _load_agent()
    client = EnsemblGraphQLClient(settings)

    def get_version() -> dict[str, Any]:
        """Return the Ensembl GraphQL API version.

        Use this only when the user asks about the Ensembl API version.
        """
        return asyncio.run(server.op_version(client))

    def get_variant(
        identifier: str,
        genome_id: str = settings.human_genome_id,
        species: str = "human",
        assembly: str = "GRCh38",
    ) -> dict[str, Any] | None:
        """Get rich annotation for a bare rsID or region:position:rsid identifier.

        Read variant location from ``slice`` and inspect every ``alleles`` item;
        multiallelic sites can have more than one alternate allele. Each allele
        carries explicitly named population frequencies. Full responses include
        phenotype assertions and transcript molecular consequences with gene,
        transcript, protein, and coordinate fields.

        Prediction scope matters: variant results include Ensembl VEP, GERP, and
        AncestralAllele; allele results include CADD; transcript-consequence
        results include SIFT, SpliceAI, and sometimes PolyPhen. Never combine
        scores from different methods or report a frequency without its population.
        """
        if ":" in identifier:
            return asyncio.run(
                server.op_get_variant(
                    client,
                    genome_id,
                    identifier,
                    settings.variation_endpoint,
                )
            )
        return asyncio.run(
            server.op_get_variant_by_rsid(
                client,
                identifier,
                genome_id,
                settings.variation_endpoint,
                species,
                assembly,
            )
        )

    def resolve_rsid(
        rsid: str,
        species: str = "human",
        assembly: str = "GRCh38",
    ) -> dict[str, Any]:
        """Resolve a bare rsID to coordinate IDs without fetching annotation."""
        return asyncio.run(server.op_resolve_rsid(client, rsid, species, assembly))

    def get_homologies(
        gene_stable_id: str,
        genome_id: str = settings.human_genome_id,
    ) -> list[dict[str, Any]]:
        """Get compara homologies for an Ensembl gene stable ID."""
        return asyncio.run(
            server.op_get_homologies(
                client,
                genome_id,
                gene_stable_id,
                settings.compara_endpoint,
            )
        )

    def get_releases() -> Any:
        """Get integrated and partial Ensembl beta release metadata."""
        return asyncio.run(server.op_get_releases(client))

    def find_genes_by_symbol(
        symbol: str, genome_id: str = settings.human_genome_id
    ) -> list[dict[str, Any]]:
        """Find Ensembl genes by display symbol in one genome.

        Use this for questions like "where is BRCA2?", "TP53 stable id", or
        "chromosome for the human p53 gene" after resolving the likely symbol.
        The response includes stable_id, symbol, name, biotype, transcript_count,
        and genomic slice coordinates.
        """
        return asyncio.run(server.op_find_genes_by_symbol(client, symbol, genome_id))

    def get_gene_by_id(
        stable_id: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a gene by Ensembl gene stable id.

        Use this when the user provides an ENSG id, versioned or unversioned,
        for example ENSG00000139618 or ENSG00000139618.19.
        """
        return asyncio.run(server.op_get_gene_by_id(client, genome_id, stable_id))

    def get_transcript(
        stable_id: str | None = None,
        symbol: str | None = None,
        genome_id: str = settings.human_genome_id,
    ) -> dict[str, Any] | None:
        """Get one transcript by Ensembl transcript stable id or transcript symbol.

        Use this for ENST ids such as ENST00000380152 or exact transcript symbols
        such as BRCA2-201. For general gene symbols like BRCA2, use
        find_genes_by_symbol first unless the user explicitly asks for transcripts.
        """
        return asyncio.run(server.op_get_transcript(client, genome_id, stable_id, symbol))

    def transcript_search(
        query: str,
        genome_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Search transcripts by identifier across one or more genomes.

        Use this for fuzzy ENST or transcript-id searches, not for gene-name
        lookup. For gene symbols such as BRCA2 or TP53, use find_genes_by_symbol.
        """
        return asyncio.run(
            server.op_transcript_search(
                client, query, genome_ids or [settings.human_genome_id], page, per_page
            )
        )

    def get_product_by_id(
        stable_id: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a product by Ensembl product stable id.

        Use this for ENSP protein product ids such as ENSP00000369497.3. The
        response includes product type and length, for example Protein length
        3418 for ENSP00000369497.3.
        """
        return asyncio.run(server.op_get_product_by_id(client, genome_id, stable_id))

    def get_region(
        name: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a genome region, such as a chromosome, by name.

        Use this when the user asks about region metadata for a chromosome or
        scaffold name, for example chromosome 13.
        """
        return asyncio.run(server.op_get_region(client, genome_id, name))

    def overlap_region(
        region_name: str,
        start: int,
        end: int,
        genome_id: str = settings.human_genome_id,
    ) -> dict[str, Any]:
        """List genes and transcripts overlapping a genomic interval.

        Use this for coordinate/locus prompts such as chr13:32315086-32400268
        by passing region_name="13", start=32315086, and end=32400268.
        The response contains separate genes and transcripts lists.
        """
        return asyncio.run(
            server.op_overlap_region(client, genome_id, region_name, start, end)
        )

    def find_genomes(
        scientific_name: str | None = None,
        common_name: str | None = None,
        ensembl_name: str | None = None,
        assembly_accession_id: str | None = None,
        tolid: str | None = None,
        species_taxonomy_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve species or assembly keywords to Ensembl genome ids.

        Use this before other tools when the user asks about a non-human species,
        assembly, common name, scientific name, or taxon id.
        """
        keyword = GenomeKeywordInput(
            scientific_name=scientific_name,
            common_name=common_name,
            ensembl_name=ensembl_name,
            assembly_accession_id=assembly_accession_id,
            tolid=tolid,
            species_taxonomy_id=species_taxonomy_id,
        )
        return asyncio.run(server.op_find_genomes(client, keyword))

    def get_genome(genome_id: str = settings.human_genome_id) -> dict[str, Any] | None:
        """Get genome metadata by genome id.

        Use this when the user provides a genome UUID or asks to verify the
        configured/default genome.
        """
        return asyncio.run(server.op_get_genome(client, genome_id))

    def get_sequence_metadata(sequence_id: str) -> dict[str, Any]:
        """Get Refget metadata for a sequence digest id.

        Use this to inspect sequence length and aliases before deciding whether
        to retrieve the actual sequence.
        """
        return asyncio.run(server.op_get_sequence_metadata(client, sequence_id))

    def get_sequence_to_file(
        sequence_id: str,
        start: int | None = None,
        end: int | None = None,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Stream a Refget sequence or subsequence to a local text file.

        Use this instead of returning sequence text when the user asks to save,
        download, or retrieve a large sequence. Refget ranges are 0-indexed and
        half-open: start is included, end is excluded.
        """
        return asyncio.run(
            server.op_get_sequence_to_file(
                client, sequence_id, settings.output_dir, start, end, output_name
            )
        )

    def graphql_query_to_file(
        query: str,
        variables: dict[str, Any] | None = None,
        output_name: str | None = None,
    ) -> dict[str, Any]:
        """Run a raw GraphQL query and write the result to a JSON file.

        Use this instead of returning raw data when a user asks for a large
        payload, a sequence-like payload, or asks to save/download results. The
        result contains the file path, byte size, and top-level JSON keys.
        """
        return asyncio.run(
            server.op_graphql_query_to_file(
                client, query, variables, settings.output_dir, output_name
            )
        )

    model = _create_model(settings, api_key)
    return agent_cls(
        name="Ensembl MCP Agent",
        model=model,
        tools=[
            get_version,
            get_variant,
            resolve_rsid,
            get_homologies,
            get_releases,
            find_genes_by_symbol,
            get_gene_by_id,
            get_transcript,
            transcript_search,
            get_product_by_id,
            get_region,
            overlap_region,
            find_genomes,
            get_genome,
            get_sequence_metadata,
            get_sequence_to_file,
            graphql_query_to_file,
        ],
        instructions=[
            "Answer questions about Ensembl beta data using the provided tools.",
            (
                "Default to the configured human reference genome id when the user "
                "does not specify a species or genome."
            ),
            "Use find_genomes before querying non-human species.",
            (
                "Parse coordinate prompts like chr13:32315086-32400268 as "
                "region_name=13, start=32315086, end=32400268."
            ),
            (
                "Use get_variant directly for bare rsIDs such as rs699 or variation "
                "IDs such as 1:230710048:rs699. Use resolve_rsid only when the user "
                "needs coordinate mappings without full annotation."
            ),
            (
                "For variants, inspect every allele: identify reference_sequence and "
                "allele_sequence, preserve all alternate alleles, and name the exact "
                "population beside each reported frequency."
            ),
            (
                "Keep predictions at their returned scope: Ensembl VEP/GERP/"
                "AncestralAllele are variant-level, CADD is allele-level, and SIFT/"
                "SpliceAI/PolyPhen are transcript-consequence-level. Do not merge "
                "their scores or infer a clinical diagnosis from them."
            ),
            (
                "Report phenotype assertions as sourced associations, not diagnoses; "
                "include the phenotype source such as ClinVar when available."
            ),
            "Use get_product_by_id for ENSP ids and get_transcript for ENST ids.",
            (
                "Use graphql_query_to_file instead of returning raw JSON when a "
                "query may produce a large payload or the user asks to save results."
            ),
            (
                "For raw Refget sequence retrieval, prefer get_sequence_to_file "
                "unless the user asks for a short subsequence inline."
            ),
            "Keep answers concise and include stable ids, symbols, or regions when useful.",
            (
                "Do not claim AlphaMissense, ESM1b, or structural-variant support: "
                "those data are not available from the wrapped API. PolyPhen may "
                "appear at transcript-consequence level when Ensembl returns it."
            ),
        ],
        markdown=True,
        tool_call_limit=8,
    )


def run_agent_query(query: str, settings: Settings | None = None) -> str:
    """Run one natural-language query through the Agno Ensembl agent."""
    response = create_agent(settings).run(query)
    if hasattr(response, "get_content_as_string"):
        return response.get_content_as_string()
    return str(getattr(response, "content", response))
