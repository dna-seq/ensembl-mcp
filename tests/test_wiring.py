import json

from fastmcp import Client

from ensembl_mcp.server import create_server


async def test_tool_annotations_match_side_effects() -> None:
    async with Client(transport=create_server()) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    local_writers = {
        "get_sequence_to_file",
        "graphql_query_to_file",
        "get_variant_to_file",
    }
    assert local_writers <= tools.keys()
    for name, tool in tools.items():
        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
        assert tool.annotations.readOnlyHint is (name not in local_writers)


async def test_new_backend_tools_are_registered() -> None:
    async with Client(transport=create_server()) as client:
        names = {tool.name for tool in await client.list_tools()}

    assert {
        "get_variant",
        "resolve_rsid",
        "batch_resolve_rsids",
        "batch_resolve_coordinates",
        "get_variant_by_rsid",
        "batch_get_variants_by_rsid",
        "list_variant_populations",
        "get_homologies",
        "get_releases",
    } <= names


async def test_variant_tools_publish_detailed_output_schemas_and_examples() -> None:
    async with Client(transport=create_server()) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    variant_tool = tools["get_variant"]
    rsid_tool = tools["get_variant_by_rsid"]
    batch_tool = tools["batch_get_variants_by_rsid"]
    schemas = json.dumps(
        [variant_tool.outputSchema, rsid_tool.outputSchema, batch_tool.outputSchema]
    )

    for field in (
        "population_frequencies",
        "phenotype_assertions",
        "predicted_molecular_consequences",
        "prediction_results",
        "gene_symbol",
        "cdna_location",
        "analysis_method",
    ):
        assert field in schemas
    for method in (
        "Ensembl VEP",
        "GERP",
        "AncestralAllele",
        "CADD",
        "SIFT",
        "SpliceAI",
        "PolyPhen",
    ):
        assert method in schemas

    assert variant_tool.description is not None
    assert "1:230710048:rs699" in variant_tool.description
    assert "gnomADe:ALL" in variant_tool.description
    assert rsid_tool.description is not None
    assert "resolution.variant_ids" in rsid_tool.description
