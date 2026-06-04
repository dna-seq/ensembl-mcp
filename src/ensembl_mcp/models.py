from pydantic import BaseModel, Field


class SymbolInput(BaseModel):
    """Mirror of the GraphQL ``SymbolInput`` type."""

    symbol: str
    genome_id: str


class IdInput(BaseModel):
    """Mirror of the GraphQL ``IdInput`` type (stable id lookup)."""

    genome_id: str
    stable_id: str


class RegionNameInput(BaseModel):
    """Mirror of the GraphQL ``RegionNameInput`` type."""

    genome_id: str
    name: str


class SliceInput(BaseModel):
    """Mirror of the GraphQL ``SliceInput`` type used by ``overlap_region``."""

    genome_id: str
    region_name: str
    start: int
    end: int


class GenomeKeywordInput(BaseModel):
    """Mirror of the GraphQL ``GenomeBySpecificKeywordInput`` type.

    Every field is optional; supply whichever keyword(s) you want to search by.
    """

    tolid: str | None = None
    assembly_accession_id: str | None = None
    assembly_name: str | None = None
    ensembl_name: str | None = None
    common_name: str | None = None
    scientific_name: str | None = None
    scientific_parlance_name: str | None = None
    species_taxonomy_id: str | None = None
    release_version: float | None = None

    def to_graphql_input(self) -> dict[str, object]:
        """Return only the populated keyword fields for the GraphQL variables."""
        return {key: value for key, value in self.model_dump().items() if value is not None}


class GeneResult(BaseModel):
    """Subset of the GraphQL ``Gene`` type returned by the bulk tool."""

    symbol: str | None = None
    name: str | None = None
    stable_id: str | None = None
    so_term: str | None = Field(default=None, description="Sequence Ontology biotype term.")
