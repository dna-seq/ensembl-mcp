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
        """Return the Ensembl GraphQL API version."""
        return asyncio.run(server.op_version(client))

    def find_genes_by_symbol(
        symbol: str, genome_id: str = settings.human_genome_id
    ) -> list[dict[str, Any]]:
        """Find Ensembl genes by display symbol, for example BRCA2."""
        return asyncio.run(server.op_find_genes_by_symbol(client, symbol, genome_id))

    def get_gene_by_id(
        stable_id: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a gene by Ensembl stable id."""
        return asyncio.run(server.op_get_gene_by_id(client, genome_id, stable_id))

    def get_transcript(
        stable_id: str | None = None,
        symbol: str | None = None,
        genome_id: str = settings.human_genome_id,
    ) -> dict[str, Any] | None:
        """Get a transcript by stable id or symbol."""
        return asyncio.run(server.op_get_transcript(client, genome_id, stable_id, symbol))

    def transcript_search(
        query: str,
        genome_ids: list[str] | None = None,
        page: int = 1,
        per_page: int = 10,
    ) -> dict[str, Any]:
        """Search transcripts by identifier across one or more genomes."""
        return asyncio.run(
            server.op_transcript_search(
                client, query, genome_ids or [settings.human_genome_id], page, per_page
            )
        )

    def get_product_by_id(
        stable_id: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a protein product by Ensembl stable id."""
        return asyncio.run(server.op_get_product_by_id(client, genome_id, stable_id))

    def get_region(
        name: str, genome_id: str = settings.human_genome_id
    ) -> dict[str, Any] | None:
        """Get a genome region, such as a chromosome, by name."""
        return asyncio.run(server.op_get_region(client, genome_id, name))

    def overlap_region(
        region_name: str,
        start: int,
        end: int,
        genome_id: str = settings.human_genome_id,
    ) -> dict[str, Any]:
        """List genes and transcripts overlapping a genomic interval."""
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
        """Resolve species or assembly keywords to Ensembl genome ids."""
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
        """Get genome metadata by genome id."""
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
