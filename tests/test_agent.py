import pytest

from ensembl_mcp.agent import get_agent_api_key, run_agent_query
from ensembl_mcp.config import Settings

pytestmark = pytest.mark.integration


def test_agent_resolves_natural_language_gene_query(settings: Settings) -> None:
    if get_agent_api_key(settings) is None:
        pytest.skip("Set ENSEMBL_MCP_AGENT_API_KEY to run Agno agent integration tests.")

    response = run_agent_query(
        "Which human chromosome contains BRCA2? Answer with the chromosome number.",
        settings,
    )

    assert "13" in response
