import asyncio
import os
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


def _is_gemini_model(model_id: str) -> bool:
    return model_id.lower().startswith("gemini")


def get_agent_api_key(settings: Settings) -> str | None:
    """Return the configured model API key without requiring one key name."""
    explicit_key = (settings.agent_api_key or "").strip()
    if explicit_key:
        return explicit_key
    if _is_gemini_model(settings.agent_model_id):
        return (
            os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
            or None
        )
    return None


def _create_model(settings: Settings, api_key: str) -> Any:
    try:
        if _is_gemini_model(settings.agent_model_id):
            from agno.models.google import Gemini

            return Gemini(
                id=settings.agent_model_id,
                api_key=api_key,
                timeout=settings.agent_timeout,
            )
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
            "Set ENSEMBL_MCP_AGENT_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY "
            "in .env or the environment to use the agent."
        )

    agent_cls = _load_agent()
    client = EnsemblGraphQLClient(settings)

    def get_version() -> dict[str, Any]:
        """Return the Ensembl GraphQL API version.

        Use this only when the user asks about the Ensembl API version.
        """
        return asyncio.run(server.op_version(client))

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

    model = _create_model(settings, api_key)
    return agent_cls(
        name="Ensembl MCP Agent",
        model=model,
        tools=[
            get_version,
            find_genes_by_symbol,
            get_gene_by_id,
            get_transcript,
            transcript_search,
            get_product_by_id,
            get_region,
            overlap_region,
            find_genomes,
            get_genome,
        ],
        instructions=[
            "Answer questions about Ensembl beta core data using the provided tools.",
            (
                "Default to the configured human reference genome id when the user "
                "does not specify a species or genome."
            ),
            "Use find_genomes before querying non-human species.",
            (
                "Parse coordinate prompts like chr13:32315086-32400268 as "
                "region_name=13, start=32315086, end=32400268."
            ),
            "Use get_product_by_id for ENSP ids and get_transcript for ENST ids.",
            "Keep answers concise and include stable ids, symbols, or regions when useful.",
            "Explain that variants and rsid lookups are out of scope for this MCP server.",
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
