"""Integration tests for Phase 1-3 enriched tools and new operations.

Tests verify that expanded GraphQL field selections, new REST tools, the
checksum→sequence bridge, and the clinical summary view all work against
the live Ensembl endpoints.
"""

from typing import Any

import pytest

from ensembl_mcp.client import EnsemblGraphQLClient
from ensembl_mcp.config import Settings
from ensembl_mcp.server import (
    op_find_genes_by_symbol,
    op_get_gene_phenotypes,
    op_get_product_by_id,
    op_get_protein_sequence,
    op_get_transcript,
    op_get_variant_by_rsid,
    op_get_variants_in_region,
    op_variant_recoder,
    _build_clinical_summary,
)

pytestmark = pytest.mark.integration


# ── Phase 1: Enriched gene/transcript/product fields ──


async def test_gene_includes_xrefs_and_metadata(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    genes = await op_find_genes_by_symbol(client, "BRCA2", human_genome_id)
    gene = genes[0]

    assert gene["symbol"] == "BRCA2"
    assert len(gene["external_references"]) > 10
    sources = {
        xref["source"]["name"]
        for xref in gene["external_references"]
        if xref.get("source")
    }
    assert "HGNC Symbol" in sources
    assert "MIM gene" in sources
    assert gene["metadata"]["name"]["accession_id"] == "HGNC:1101"
    assert gene["metadata"]["biotype"]["value"] == "protein_coding"
    assert "FANCD1" in gene["alternative_symbols"]


async def test_gene_includes_transcripts_with_mane_flags(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    genes = await op_find_genes_by_symbol(client, "BRCA2", human_genome_id)
    transcripts = genes[0]["transcripts"]

    assert len(transcripts) >= 10
    mane_select = next(
        (
            tx
            for tx in transcripts
            if (tx.get("metadata") or {}).get("mane", {}).get("value") == "select"
        ),
        None,
    )
    assert mane_select is not None
    assert mane_select["symbol"] == "BRCA2-201"
    assert mane_select["metadata"]["canonical"]["value"] is True


async def test_transcript_includes_exons_and_cds(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    tx = await op_get_transcript(
        client, human_genome_id, stable_id="ENST00000380152"
    )

    assert tx is not None
    assert tx["metadata"]["mane"]["value"] == "select"
    assert tx["metadata"]["mane"]["ncbi_transcript"]["id"] == "NM_000059.4"
    assert tx["metadata"]["canonical"]["value"] is True

    exons = tx["spliced_exons"]
    assert len(exons) == 27
    assert exons[0]["index"] == 1
    assert exons[0]["exon"]["stable_id"].startswith("ENSE")

    pgcs = tx["product_generating_contexts"]
    assert len(pgcs) >= 1
    cds = pgcs[0]["cds"]
    assert cds["protein_length"] == 3418
    assert cds["nucleotide_length"] > 0

    product = pgcs[0]["product"]
    assert product["stable_id"].startswith("ENSP")
    assert product["sequence"]["checksum"] is not None


async def test_product_includes_domains_and_xrefs(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    product = await op_get_product_by_id(
        client, human_genome_id, "ENSP00000369497.3"
    )

    assert product is not None
    assert product["sequence"]["checksum"] == "92addb948c6c652abc1dcecca05f26c0"
    assert product["sequence"]["alphabet"]["value"] == "amino_acid_alphabet"

    domains = product["family_matches"]
    assert len(domains) >= 5
    pfam_ids = {
        fm["sequence_family"]["accession_id"]
        for fm in domains
        if fm["sequence_family"]["source"]["name"] == "Pfam"
    }
    assert "PF00634" in pfam_ids

    assert len(product["external_references"]) > 10
    sources = {
        xref["source"]["name"]
        for xref in product["external_references"]
        if xref.get("source")
    }
    assert "PDB" in sources or "Reactome" in sources


async def test_variant_predictions_include_qualifier(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    result = await op_get_variant_by_rsid(
        client,
        "rs28934578",
        human_genome_id,
        settings.variation_endpoint,
    )
    variant = result["variants"][0]

    spliceai_qualifiers = set()
    for allele in variant["alleles"]:
        for mc in allele.get("predicted_molecular_consequences") or []:
            for pr in mc.get("prediction_results") or []:
                method = pr["analysis_method"]
                if method["tool"] == "SpliceAI" and method.get("qualifier"):
                    spliceai_qualifiers.add(method["qualifier"]["result_type"])

    assert "Delta score for donor gain" in spliceai_qualifiers
    assert "Delta score for acceptor gain" in spliceai_qualifiers


# ── Phase 2: New tools ──


async def test_get_variants_in_region_returns_tp53_variants(
    client: EnsemblGraphQLClient,
) -> None:
    result = await op_get_variants_in_region(
        client, "17", 7675080, 7675100
    )

    assert result["total"] > 0
    ids = {v["id"] for v in result["variants"] if v.get("id")}
    assert any("rs" in vid for vid in ids)
    assert any(
        v.get("clinical_significance")
        for v in result["variants"]
    )


async def test_get_protein_sequence_by_gene_symbol(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    result = await op_get_protein_sequence(
        client, human_genome_id, gene_symbol="BRCA2"
    )

    assert result["gene_symbol"] == "BRCA2"
    assert result["is_canonical"] is True
    assert result["length"] == 3418
    assert len(result["sequence"]) == 3418
    assert result["sequence"].startswith("M")
    assert result["mane"]["value"] == "select"


async def test_get_protein_sequence_by_product_id(
    client: EnsemblGraphQLClient, human_genome_id: str
) -> None:
    result = await op_get_protein_sequence(
        client, human_genome_id, product_stable_id="ENSP00000369497.3"
    )

    assert result["product_stable_id"] == "ENSP00000369497.3"
    assert result["length"] == 3418
    assert len(result["sequence"]) == 3418


async def test_get_gene_phenotypes_returns_associations(
    client: EnsemblGraphQLClient,
) -> None:
    result = await op_get_gene_phenotypes(client, "TP53")

    assert result["total"] > 50
    descriptions = {p.get("description", "").lower() for p in result["phenotypes"]}
    assert any("cancer" in d or "carcinoma" in d or "tumor" in d for d in descriptions)


async def test_variant_recoder_converts_rsid(
    client: EnsemblGraphQLClient,
) -> None:
    result = await op_variant_recoder(client, "rs699")

    assert len(result) > 0
    first = result[0]
    allele_data = next(iter(first.values()))
    assert "hgvsp" in allele_data
    assert any("p.Met259Thr" in h for h in allele_data["hgvsp"])
    assert "spdi" in allele_data


# ── Phase 3: Clinical summary ──


async def test_clinical_summary_filters_populations(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    result = await op_get_variant_by_rsid(
        client,
        "rs699",
        human_genome_id,
        settings.variation_endpoint,
        full=True,
    )
    variant = result["variants"][0]

    summary = _build_clinical_summary(variant)
    assert summary["name"] == "rs699"
    assert summary["location"]["region"] == "1"

    alt_allele = next(
        (a for a in summary["alleles"] if a["allele_sequence"] == "G"), None
    )
    assert alt_allele is not None

    pop_names = {f["population"] for f in alt_allele["frequencies"]}
    assert pop_names <= {"gnomADe:ALL", "gnomADg:ALL", "1000GENOMES:phase_3:ALL"}
    assert len(alt_allele["frequencies"]) <= 3

    custom = _build_clinical_summary(variant, populations=["gnomADe:afr"])
    custom_alt = next(
        (a for a in custom["alleles"] if a["allele_sequence"] == "G"), None
    )
    assert all(f["population"] == "gnomADe:afr" for f in custom_alt["frequencies"])


async def test_clinical_summary_includes_predictions_and_consequences(
    client: EnsemblGraphQLClient,
    settings: Settings,
    human_genome_id: str,
) -> None:
    result = await op_get_variant_by_rsid(
        client,
        "rs28934578",
        human_genome_id,
        settings.variation_endpoint,
        full=True,
    )
    variant = result["variants"][0]
    summary = _build_clinical_summary(variant)

    assert any(
        p["tool"] == "GERP" for p in summary["variant_predictions"]
    )

    alt_alleles = [
        a for a in summary["alleles"]
        if a["allele_type"] and a["allele_type"] != "biological_region"
        and a.get("consequences")
    ]
    assert len(alt_alleles) > 0

    for allele in alt_alleles:
        tp53_cons = [
            c for c in allele.get("consequences", [])
            if c.get("gene_symbol") == "TP53"
        ]
        if tp53_cons:
            cons = tp53_cons[0]
            assert "missense_variant" in cons["consequences"]
            assert cons.get("sift_score") is not None
            assert cons["protein_position"] == 175
            break
    else:
        pytest.fail("No TP53 consequence found in clinical summary")
