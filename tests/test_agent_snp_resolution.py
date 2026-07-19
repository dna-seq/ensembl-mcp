import json
from pathlib import Path

import pytest

from ensembl_mcp.agent import get_agent_api_key, run_agent_query
from ensembl_mcp.config import Settings

pytestmark = pytest.mark.integration

SNPS = json.loads(
    (Path(__file__).parent.parent / "data" / "test" / "pathogenic_snps.json").read_text()
)
SNPS_BY_RSID = {snp["rsid"]: snp for snp in SNPS}


def _require_agent_key(settings: Settings) -> None:
    if get_agent_api_key(settings) is None:
        pytest.skip(
            "Set ENSEMBL_MCP_AGENT_API_KEY to run Agno agent integration tests."
        )


# -- rsID → coordinates and annotation --


def test_agent_resolves_rsid_to_coordinates_clcn1(settings: Settings) -> None:
    """rs55960271 in CLCN1 on chromosome 7."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs55960271"]

    response = run_agent_query(
        "What are the genomic coordinates and alleles for variant rs55960271 in human? "
        "Return the chromosome number, position, reference allele, and every alternative "
        "allele currently returned by Ensembl.",
        settings,
    )

    assert snp["chrom"] in response
    assert "C" in response
    assert "A" in response
    assert "T" in response


def test_agent_resolves_rsid_to_coordinates_mmp20(settings: Settings) -> None:
    """rs587777516 in MMP20 on chromosome 11."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs587777516"]

    response = run_agent_query(
        "Resolve rs587777516 to its GRCh38 coordinates. "
        "Give me the chromosome, position, and alleles.",
        settings,
    )

    assert snp["chrom"] in response
    assert "C" in response
    assert "T" in response


def test_agent_resolves_rsid_to_coordinates_cdkn2b(settings: Settings) -> None:
    """rs1063192 in CDKN2B on chromosome 9."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs1063192"]

    response = run_agent_query(
        "Where is rs1063192 located in the human genome? "
        "Return chromosome, position, and the reference/alternative alleles.",
        settings,
    )

    assert snp["chrom"] in response
    assert "G" in response
    assert "A" in response


def test_agent_returns_annotation_detail_for_clcn1_variant(
    settings: Settings,
) -> None:
    """Ask about rs55960271 and expect sourced phenotype/gene annotation."""
    _require_agent_key(settings)

    response = run_agent_query(
        "Use the full live annotation for human rs55960271. State the affected gene, "
        "at least one phenotype association exactly as returned, and the phenotype "
        "source. Describe it as an association rather than diagnosing anyone.",
        settings,
    )

    assert "CLCN1" in response.upper()
    assert "MYOTON" in response.upper()
    assert "CLINVAR" in response.upper()


def test_agent_preserves_variant_annotation_levels_for_rs699(
    settings: Settings,
) -> None:
    """The agent should not flatten frequencies or prediction scopes."""
    _require_agent_key(settings)

    response = run_agent_query(
        "Inspect the full live human annotation for rs699. Report its GRCh38 "
        "coordinate, reference and alternate alleles, affected gene, one frequency "
        "for the G allele with the exact population name, and group available "
        "prediction methods by variant, allele, and transcript-consequence level. "
        "Do not combine their scores.",
        settings,
    )
    normalized = response.upper().replace(",", "")

    assert "230710048" in normalized
    assert "AGT" in normalized
    assert "GNOMADE:ALL" in normalized
    assert "CADD" in normalized
    assert "GERP" in normalized
    assert "SIFT" in normalized
    assert "SPLICEAI" in normalized


# -- coordinates → rsID and gene --


def test_agent_finds_gene_at_clcn1_locus(settings: Settings) -> None:
    """Given CLCN1 locus coordinates, expect the agent to identify the gene."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs55960271"]

    response = run_agent_query(
        f"What gene overlaps position {snp['start']} on chromosome {snp['chrom']} "
        "in the human genome? Return the gene symbol and Ensembl gene stable id.",
        settings,
    )

    assert "CLCN1" in response.upper()


def test_agent_finds_gene_at_mmp20_locus(settings: Settings) -> None:
    """Given MMP20 locus coordinates, expect the agent to identify the gene."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs587777516"]

    response = run_agent_query(
        f"What gene is at position {snp['start']} on chromosome {snp['chrom']} "
        "in the human genome?",
        settings,
    )

    assert "MMP20" in response.upper()


def test_agent_finds_gene_at_cdkn2b_locus(settings: Settings) -> None:
    """Given CDKN2B locus coordinates, expect the agent to identify the gene."""
    _require_agent_key(settings)
    snp = SNPS_BY_RSID["rs1063192"]

    response = run_agent_query(
        f"In human, what gene overlaps the position chr{snp['chrom']}:{snp['start']}? "
        "Return the gene symbol.",
        settings,
    )

    assert "CDKN2B" in response.upper()


# -- batch resolution --


def test_agent_batch_resolves_multiple_pathogenic_rsids(
    settings: Settings,
) -> None:
    """Ask the agent to resolve three rsIDs at once."""
    _require_agent_key(settings)

    response = run_agent_query(
        "Resolve these three variant rsIDs to their human GRCh38 chromosomes: "
        "rs55960271, rs587777516, rs1063192. "
        "For each, give the chromosome number.",
        settings,
    )

    assert "7" in response
    assert "11" in response
    assert "9" in response
