import pytest

from ensembl_mcp.agent import get_agent_api_key, run_agent_query
from ensembl_mcp.config import Settings

pytestmark = pytest.mark.integration


def _compact_number_format(text: str) -> str:
    return text.replace(",", "")


def _require_agent_key(settings: Settings) -> None:
    if get_agent_api_key(settings) is None:
        pytest.skip(
            "Set ENSEMBL_MCP_AGENT_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY "
            "to run Agno agent integration tests."
        )


def test_agent_resolves_natural_language_gene_query(settings: Settings) -> None:
    _require_agent_key(settings)

    response = run_agent_query(
        "Which human chromosome contains BRCA2? Answer with the chromosome number.",
        settings,
    )

    assert "13" in response


def test_agent_resolves_gene_symbol_with_synonym_language(settings: Settings) -> None:
    _require_agent_key(settings)

    response = run_agent_query(
        (
            "In human, I mean the tumor protein p53 gene. Give me its HGNC symbol, "
            "Ensembl gene stable id, and chromosome. Do not discuss variants."
        ),
        settings,
    )

    assert "TP53" in response.upper()
    assert "ENSG00000141510" in response
    assert "17" in response


def test_agent_interprets_human_locus_overlap_query(settings: Settings) -> None:
    _require_agent_key(settings)

    response = run_agent_query(
        (
            "For the human locus chr13:32315086-32400268, which gene overlaps it? "
            "Return the gene symbol and Ensembl gene stable id."
        ),
        settings,
    )

    assert "BRCA2" in response.upper()
    assert "ENSG00000139618" in response


def test_agent_handles_product_stable_id_query(settings: Settings) -> None:
    _require_agent_key(settings)

    response = run_agent_query(
        (
            "ENSP00000369497.3 is an Ensembl product stable id. "
            "What product type is it, and what is its length?"
        ),
        settings,
    )

    assert "PROTEIN" in response.upper()
    assert "3418" in _compact_number_format(response)
