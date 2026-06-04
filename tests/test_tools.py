from pathlib import Path

import httpx
import pytest

from ensembl_mcp import server
from ensembl_mcp.client import EnsemblGraphQLClient, GraphQLError
from ensembl_mcp.models import GenomeKeywordInput

pytestmark = pytest.mark.integration


def _skip_refget_error(error: httpx.HTTPError) -> None:
    pytest.skip(f"Ensembl Refget endpoint unreachable: {error}")


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


async def test_graphql_query_to_file(
    client: EnsemblGraphQLClient, tmp_path: Path
) -> None:
    result = await server.op_graphql_query_to_file(
        client,
        "{ version { api { major minor patch } } }",
        None,
        str(tmp_path),
        "version_result.json",
    )

    output_path = tmp_path / "version_result.json"
    assert result["path"] == str(output_path)
    assert result["bytes"] == output_path.stat().st_size
    assert result["keys"] == ["version"]
    assert '"version"' in output_path.read_text()


async def test_get_sequence(client: EnsemblGraphQLClient) -> None:
    # A known sequence ID on the Ensembl Refget server
    seq_id = "92addb948c6c652abc1dcecca05f26c0"
    try:
        seq = await server.op_get_sequence(client, seq_id, start=0, end=20)
    except httpx.HTTPError as error:
        _skip_refget_error(error)
    assert len(seq) == 20
    assert seq.isalpha()


async def test_get_sequence_to_file(
    client: EnsemblGraphQLClient, tmp_path: Path
) -> None:
    seq_id = "92addb948c6c652abc1dcecca05f26c0"
    try:
        result = await server.op_get_sequence_to_file(
            client,
            seq_id,
            str(tmp_path),
            start=0,
            end=20,
            output_name="refget_sequence.txt",
        )
    except httpx.HTTPError as error:
        _skip_refget_error(error)

    output_path = tmp_path / "refget_sequence.txt"
    sequence = output_path.read_text()
    assert result["path"] == str(output_path)
    assert result["bytes"] == 20
    assert result["sequence_id"] == seq_id
    assert result["start"] == 0
    assert result["end"] == 20
    assert len(sequence) == 20
    assert sequence.isalpha()


async def test_get_sequence_metadata(client: EnsemblGraphQLClient) -> None:
    seq_id = "92addb948c6c652abc1dcecca05f26c0"
    try:
        metadata = await server.op_get_sequence_metadata(client, seq_id)
    except httpx.HTTPError as error:
        _skip_refget_error(error)
    assert "metadata" in metadata
    assert "length" in metadata["metadata"]
    assert metadata["metadata"]["length"] > 0

