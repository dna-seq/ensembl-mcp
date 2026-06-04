import pytest

from ensembl_mcp import server
from ensembl_mcp.client import EnsemblGraphQLClient

pytestmark = pytest.mark.integration


async def test_bulk_find_genes_resolves_known_and_unknown(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    result = await server.op_bulk_find_genes(
        client, ["BRCA2", "TP53", "NOT_A_REAL_GENE_SYMBOL"], human_genome_id
    )
    found_symbols = {gene["symbol"] for gene in result["found"]}
    missing_symbols = {entry["symbol"] for entry in result["missing"]}
    assert {"BRCA2", "TP53"} <= found_symbols
    assert "NOT_A_REAL_GENE_SYMBOL" in missing_symbols
