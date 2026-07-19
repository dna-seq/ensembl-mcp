from typing import Any

import pytest

from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import Settings
from ensembl_mcp.models import VariantAnnotation, VariantLookupResult
from ensembl_mcp.server import (
    op_batch_get_variants_by_rsid,
    op_batch_resolve_coordinates,
    op_batch_resolve_rsids,
    op_get_homologies,
    op_get_releases,
    op_get_variant,
    op_get_variant_by_rsid,
    op_list_variant_populations,
    op_resolve_rsid,
)

pytestmark = pytest.mark.integration


def _prediction_tools(variant: dict[str, Any]) -> set[str]:
    tools = {
        result["analysis_method"]["tool"]
        for result in variant.get("prediction_results") or []
        if result.get("analysis_method", {}).get("tool")
    }
    for allele in variant.get("alleles") or []:
        tools.update(
            result["analysis_method"]["tool"]
            for result in allele.get("prediction_results") or []
            if result.get("analysis_method", {}).get("tool")
        )
        for consequence in allele.get("predicted_molecular_consequences") or []:
            tools.update(
                result["analysis_method"]["tool"]
                for result in consequence.get("prediction_results") or []
                if result.get("analysis_method", {}).get("tool")
            )
    return tools


async def test_resolve_rsid_to_variation_identifier(
    client: EnsemblGraphQLClient,
) -> None:
    result = await op_resolve_rsid(client, "699")

    assert result["rsid"] == "rs699"
    assert result["variant_ids"] == ["1:230710048:rs699"]
    assert result["mappings"][0]["allele_string"] == "A/G"


async def test_get_variant_by_rsid_returns_rich_live_annotation(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    result = await op_get_variant_by_rsid(
        client,
        "rs699",
        human_genome_id,
        settings.variation_endpoint,
    )

    assert result["resolution"]["variant_ids"] == ["1:230710048:rs699"]
    variant = result["variants"][0]
    assert variant["name"] == "rs699"
    assert variant["slice"]["region"]["name"] == "1"
    assert {allele["allele_sequence"] for allele in variant["alleles"]} == {"A", "G"}
    assert {"CADD", "SIFT", "SpliceAI"} <= _prediction_tools(variant)
    typed = VariantLookupResult.model_validate(result)
    assert typed.resolution.variant_ids == ["1:230710048:rs699"]
    assert typed.variants[0].slice is not None
    assert typed.variants[0].slice.location is not None
    assert typed.variants[0].slice.location.start == 230710048

    alternate = next(
        allele for allele in typed.variants[0].alleles if allele.allele_sequence == "G"
    )
    assert alternate.reference_sequence == "A"
    assert any(
        result.analysis_method.tool == "CADD" and result.score == pytest.approx(0.09)
        for result in alternate.prediction_results
    )
    assert any(
        frequency.population_name == "gnomADe:ALL"
        and frequency.allele_count is not None
        and frequency.allele_number is not None
        for frequency in alternate.population_frequencies
    )
    assert any(
        consequence.gene_symbol == "AGT"
        and any(term.value == "missense_variant" for term in consequence.consequences)
        for consequence in alternate.predicted_molecular_consequences or []
    )
    assert any(
        result.analysis_method.tool == "PolyPhen"
        for consequence in alternate.predicted_molecular_consequences or []
        for result in consequence.prediction_results
    )


async def test_tp53_hotspot_exposes_prediction_scores(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    variant = await op_get_variant(
        client,
        human_genome_id,
        "17:7675088:rs28934578",
        settings.variation_endpoint,
    )

    assert variant is not None
    assert variant["name"] == "rs28934578"
    assert {"CADD", "SIFT", "SpliceAI"} <= _prediction_tools(variant)
    typed = VariantAnnotation.model_validate(variant)
    assert typed.slice is not None
    assert typed.slice.location is not None
    assert typed.slice.location.start == 7675088
    assert any(
        result.analysis_method.tool == "GERP" and result.score == pytest.approx(3.36)
        for result in typed.prediction_results
    )
    assert any(
        consequence.gene_symbol == "TP53"
        for allele in typed.alleles
        for consequence in allele.predicted_molecular_consequences or []
    )


async def test_compact_variant_validates_without_full_only_fields(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    variant = await op_get_variant(
        client,
        human_genome_id,
        "1:230710048:rs699",
        settings.variation_endpoint,
        full=False,
    )

    assert variant is not None
    typed = VariantAnnotation.model_validate(variant)
    assert typed.name == "rs699"
    assert all(allele.phenotype_assertions is None for allele in typed.alleles)
    assert all(
        allele.predicted_molecular_consequences is None for allele in typed.alleles
    )


async def test_populations_query_works_without_buggy_size_field(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    populations = await op_list_variant_populations(
        client,
        human_genome_id,
        settings.variation_endpoint,
    )

    assert len(populations) >= 52
    assert all("size" not in population for population in populations)
    assert any(
        "gnomad" in population["display_group_name"].lower()
        and "genome" in population["display_group_name"].lower()
        for population in populations
    )


async def test_batch_rsid_operations_preserve_missing_outcomes(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    rsids = ["rs699", "rs999999999999999999"]
    resolutions = await op_batch_resolve_rsids(client, rsids)
    variants = await op_batch_get_variants_by_rsid(
        client,
        rsids,
        human_genome_id,
        settings.variation_endpoint,
    )

    assert [item["rsid"] for item in resolutions["resolved"]] == ["rs699"]
    assert [item["rsid"] for item in resolutions["missing"]] == [rsids[1]]
    assert variants["found"][0]["variants"][0]["name"] == "rs699"
    assert [item["rsid"] for item in variants["missing"]] == [rsids[1]]


async def test_batch_coordinate_resolution_returns_overlapping_rsids(
    client: EnsemblGraphQLClient,
) -> None:
    result = await op_batch_resolve_coordinates(
        client,
        ["chr1:230710048", "1:1"],
    )

    assert result["found"][0]["coordinate"] == "1:230710048"
    assert "rs699" in {variation["id"] for variation in result["found"][0]["variations"]}
    assert result["missing"] == [
        {
            "coordinate": "1:1",
            "reason": "No variations found",
        }
    ]


async def test_live_release_metadata_and_compara_contract(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    releases = await op_get_releases(client)
    homologies = await op_get_homologies(
        client,
        human_genome_id,
        "ENSG00000139618",
        settings.compara_endpoint,
    )

    assert any(release["type"] == "integrated" and release["is_current"] for release in releases)
    assert any(release["type"] == "partial" and release["is_current"] for release in releases)
    assert isinstance(homologies, list)
