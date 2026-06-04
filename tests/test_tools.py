import httpx
import pytest

from ensembl_mcp import server
from ensembl_mcp.client import EnsemblGraphQLClient, GraphQLError
from ensembl_mcp.models import GenomeKeywordInput

pytestmark = pytest.mark.integration


async def test_find_genes_by_symbol(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    genes = await server.op_find_genes_by_symbol(client, "BRCA2", human_genome_id)
    assert any(g["stable_id"].startswith("ENSG00000139618") for g in genes)


async def test_get_gene_by_id(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    gene = await server.op_get_gene_by_id(client, human_genome_id, "ENSG00000139618")
    assert gene is not None
    assert gene["symbol"] == "BRCA2"
    assert gene["slice"]["region"]["name"] == "13"


async def test_get_transcript_by_id(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    transcript = await server.op_get_transcript(
        client, human_genome_id, stable_id="ENST00000380152"
    )
    assert transcript is not None
    assert transcript["stable_id"].startswith("ENST00000380152")


async def test_get_transcript_requires_an_identifier(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    with pytest.raises(ValueError):
        await server.op_get_transcript(client, human_genome_id)


async def test_get_product_by_id(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    product = await server.op_get_product_by_id(
        client, human_genome_id, "ENSP00000369497.3"
    )
    assert product is not None
    assert product["type"] == "Protein"
    assert product["length"] > 0


async def test_get_region(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    region = await server.op_get_region(client, human_genome_id, "13")
    assert region is not None
    assert region["name"] == "13"
    assert region["code"] == "chromosome"


async def test_overlap_region_finds_brca2(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    locus = await server.op_overlap_region(client, human_genome_id, "13", 32315086, 32400268)
    symbols = {gene.get("symbol") for gene in locus["genes"]}
    assert "BRCA2" in symbols


async def test_get_genome(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    genome = await server.op_get_genome(client, human_genome_id)
    assert genome is not None
    assert genome["scientific_name"] == "Homo sapiens"
    assert genome["genome_id"] == human_genome_id


async def test_transcript_search_returns_meta(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    result = await server.op_transcript_search(client, "BRCA2", [human_genome_id], 1, 5)
    assert isinstance(result["meta"]["total_hits"], int)
    assert isinstance(result["matches"], list)


async def test_find_genomes_resolves_human(client: EnsemblGraphQLClient) -> None:
    keyword = GenomeKeywordInput(scientific_name="Homo sapiens")
    try:
        genomes = await server.op_find_genomes(client, keyword)
    except (httpx.HTTPStatusError, GraphQLError) as error:
        pytest.skip(f"Ensembl genome keyword search is currently failing: {error}")
    assert any(g["scientific_name"] == "Homo sapiens" for g in genomes)
