import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


# ── Core GraphQL response models (extra="ignore" for additive API fields) ──


class CoreResponseModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ExternalDBRef(CoreResponseModel):
    """Source database for a cross-reference."""

    name: str | None = None
    url: str | None = None


class AssignmentMethod(CoreResponseModel):
    """How a cross-reference was assigned."""

    type: str | None = None
    description: str | None = None


class CoreExternalReference(CoreResponseModel):
    """Cross-reference linking an Ensembl object to an external database."""

    accession_id: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None
    source: ExternalDBRef | None = None
    assignment_method: AssignmentMethod | None = None


class NameSource(CoreResponseModel):
    """Source of a gene name (e.g. HGNC)."""

    name: str | None = None
    url: str | None = None


class GeneNameMetadata(CoreResponseModel):
    """HGNC or equivalent gene name provenance."""

    accession_id: str | None = None
    value: str | None = None
    url: str | None = None
    source: NameSource | None = None


class BiotypeMetadata(CoreResponseModel):
    """Gene or transcript biotype classification."""

    value: str | None = None
    label: str | None = None
    definition: str | None = None


class GeneMetadata(CoreResponseModel):
    """Gene-level metadata: biotype and name provenance."""

    biotype: BiotypeMetadata | None = None
    name: GeneNameMetadata | None = None


class NCBITranscript(CoreResponseModel):
    """NCBI RefSeq transcript linked from MANE metadata."""

    id: str | None = None
    url: str | None = None


class ManeMetadata(CoreResponseModel):
    """MANE Select / MANE Plus Clinical metadata."""

    value: str | None = None
    label: str | None = None
    ncbi_transcript: NCBITranscript | None = None


class FlagMetadata(CoreResponseModel):
    """Generic boolean/string flag used for canonical, APPRIS, TSL, GENCODE basic."""

    value: str | bool | None = None
    label: str | None = None


class TranscriptMetadata(CoreResponseModel):
    """Transcript quality and clinical designation flags."""

    mane: ManeMetadata | None = None
    canonical: FlagMetadata | None = None
    appris: FlagMetadata | None = None
    tsl: FlagMetadata | None = None
    gencode_basic: FlagMetadata | None = None


class ExonSliceLocation(CoreResponseModel):
    start: int | None = None
    end: int | None = None


class ExonSliceRegion(CoreResponseModel):
    name: str | None = None


class ExonSlice(CoreResponseModel):
    region: ExonSliceRegion | None = None
    location: ExonSliceLocation | None = None


class Exon(CoreResponseModel):
    """A single exon with its genomic coordinates."""

    stable_id: str | None = None
    slice: ExonSlice | None = None


class RelativeLocation(CoreResponseModel):
    """Position relative to the transcript."""

    start: int | None = None
    end: int | None = None
    length: int | None = None


class SplicedExon(CoreResponseModel):
    """An exon in transcript context: its index and both relative and genomic position."""

    index: int | None = None
    relative_location: RelativeLocation | None = None
    exon: Exon | None = None


class CDS(CoreResponseModel):
    """Coding sequence boundaries and lengths."""

    start: int | None = None
    end: int | None = None
    protein_length: int | None = None
    nucleotide_length: int | None = None


class UTR(CoreResponseModel):
    """5' or 3' untranslated region."""

    start: int | None = None
    end: int | None = None
    length: int | None = None


class SequenceInfo(CoreResponseModel):
    """Sequence digest and alphabet."""

    checksum: str | None = None
    alphabet: BiotypeMetadata | None = Field(
        default=None, description="Alphabet type, e.g. amino_acid_alphabet."
    )


class ProductSummary(CoreResponseModel):
    """Compact protein product from a transcript context."""

    stable_id: str | None = None
    unversioned_stable_id: str | None = None
    length: int | None = None
    sequence: SequenceInfo | None = None


class ProductGeneratingContext(CoreResponseModel):
    """Transcript-to-protein relationship with CDS/UTR boundaries."""

    product_type: str | None = None
    default: bool | None = None
    cds: CDS | None = None
    five_prime_utr: UTR | None = None
    three_prime_utr: UTR | None = None
    product: ProductSummary | None = None


class SequenceFamilySource(CoreResponseModel):
    name: str | None = None
    url: str | None = None


class SequenceFamily(CoreResponseModel):
    """Domain/family database entry (Pfam, PANTHER, etc.)."""

    source: SequenceFamilySource | None = None
    accession_id: str | None = None
    name: str | None = None
    description: str | None = None


class FamilyMatch(CoreResponseModel):
    """A protein domain hit with position and statistical significance."""

    sequence_family: SequenceFamily | None = None
    relative_location: RelativeLocation | None = None
    hit_location: RelativeLocation | None = None
    score: float | None = None
    evalue: float | None = None


class VariantResponseModel(BaseModel):
    """Base for typed variation responses while tolerating additive API fields."""

    model_config = ConfigDict(extra="ignore")


class OntologyValue(VariantResponseModel):
    """An ontology-like accession and human-readable value."""

    accession_id: str | None = Field(
        description="Ontology/accession identifier; currently often null in variation results."
    )
    value: str | None = Field(description="Human-readable value or classification.")


class ExternalReference(VariantResponseModel):
    """Named source or alternative identifier with optional provenance links."""

    accession_id: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None


class SourceReference(VariantResponseModel):
    """Source database and release metadata for phenotype evidence."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None
    release: str | None = None


class SequenceLocation(VariantResponseModel):
    """One-based inclusive location and its length."""

    start: int | None = None
    end: int | None = None
    length: int | None = None


class RegionReference(VariantResponseModel):
    """Reference region such as chromosome 1."""

    name: str | None = None


class Strand(VariantResponseModel):
    """Named and numeric strand representation."""

    code: str | None = Field(default=None, description="For example, 'forward'.")
    value: int | None = Field(default=None, description="Usually 1 or -1.")


class VariantSlice(VariantResponseModel):
    """Genomic region, coordinates, and strand for a variant."""

    region: RegionReference | None = None
    location: SequenceLocation | None = None
    strand: Strand | None = None


class Qualifier(VariantResponseModel):
    """Label distinguishing prediction sub-scores (e.g. SpliceAI delta types)."""

    result_type: str | None = Field(
        default=None,
        description="What the score measures, e.g. 'Delta score for acceptor gain'.",
    )
    modes: list[str] | None = Field(
        default=None,
        description="Computation modes, e.g. ['masked scores'].",
    )


class AnalysisMethod(VariantResponseModel):
    """Prediction/annotation method that produced a result."""

    tool: str = Field(
        description=(
            "Method name, such as Ensembl VEP, GERP, AncestralAllele, CADD, "
            "SIFT, SpliceAI, or PolyPhen."
        )
    )
    version: str | None = None
    qualifier: Qualifier | None = Field(
        default=None,
        description="Sub-score label; critical for SpliceAI where 8 deltas exist per consequence.",
    )


class PredictionResult(VariantResponseModel):
    """Method-specific prediction; interpret in the context of ``analysis_method``."""

    score: float | None = Field(
        description=(
            "Method-specific numeric score. Scales are not interchangeable between tools."
        )
    )
    result: str | None = Field(
        description="Method-specific textual result, such as a VEP consequence."
    )
    classification: OntologyValue | None = Field(
        description="Optional method-specific classification; values may be null."
    )
    analysis_method: AnalysisMethod


class PopulationFrequency(VariantResponseModel):
    """Frequency of one allele in one explicitly named population panel."""

    population_name: str = Field(
        description=(
            "Exact population panel, for example 'gnomADe:ALL' or a specific ancestry. "
            "Never compare frequencies without naming the panel."
        )
    )
    allele_frequency: float | None
    allele_count: int | None = Field(
        description="Observed copies of this allele; null for some inferred reference alleles."
    )
    allele_number: int | None = Field(
        description="Total called alleles; null for some inferred reference alleles."
    )
    is_minor_allele: bool | None
    is_hpmaf: bool | None = Field(
        description="Whether this is the highest population minor allele frequency."
    )


class OntologyTerm(VariantResponseModel):
    """Ontology term attached to a phenotype."""

    accession_id: str | None = None
    name: str | None = None
    description: str | None = None
    url: str | None = None


class Phenotype(VariantResponseModel):
    """Reported phenotype and its source."""

    name: str | None = None
    source: SourceReference | None = None
    ontology_terms: list[OntologyTerm] | None = Field(
        default=None,
        description="Ontology mappings when supplied; currently often null.",
    )


class PhenotypeEvidenceAssertion(VariantResponseModel):
    """Evidence assertion, including ValueSet fields when returned."""

    label: str | None = None
    definition: str | None = None
    description: str | None = None
    accession_id: str | None = None
    value: str | None = None
    is_current: bool | None = None


class PhenotypeEvidence(VariantResponseModel):
    """Source and assertion supporting a phenotype association."""

    source: SourceReference | None = None
    assertion: PhenotypeEvidenceAssertion | None = None


class PhenotypeAssertion(VariantResponseModel):
    """A phenotype association reported for a variant allele."""

    feature: str | None = Field(default=None, description="Usually the rsID.")
    feature_type: OntologyValue | None = None
    phenotype: Phenotype | None = None
    evidence: list[PhenotypeEvidence] = Field(default_factory=list)


class MolecularConsequence(VariantResponseModel):
    """Transcript-level molecular consequence for one allele."""

    allele_name: str | None = None
    stable_id: str | None = Field(
        default=None, description="Affected feature stable ID, normally a transcript."
    )
    feature_type: OntologyValue | None = None
    consequences: list[OntologyValue] = Field(
        default_factory=list,
        description="Sequence Ontology consequence terms such as missense_variant.",
    )
    gene_stable_id: str | None = None
    gene_symbol: str | None = None
    protein_stable_id: str | None = None
    transcript_biotype: str | None = None
    cdna_location: SequenceLocation | None = None
    cds_location: SequenceLocation | None = None
    protein_location: SequenceLocation | None = None
    prediction_results: list[PredictionResult] = Field(
        default_factory=list,
        description=(
            "Transcript-consequence predictions, including SIFT, SpliceAI, and "
            "currently observed PolyPhen results."
        ),
    )


class VariantAlleleDisplayData(VariantResponseModel):
    """Summary counts and representative frequency shown by Ensembl."""

    count_transcript_consequences: int | None = None
    count_overlapped_genes: int | None = None
    count_regulatory_consequences: int | None = None
    count_variant_phenotypes: int | None = None
    count_gene_phenotypes: int | None = None
    representative_population_allele_frequency: float | None = None


class VariantAllele(VariantResponseModel):
    """Reference or alternate allele and its annotations."""

    name: str | None = Field(
        default=None, description="Coordinate allele ID, for example '1:230710048:A:G'."
    )
    allele_sequence: str | None = None
    reference_sequence: str | None = None
    allele_type: OntologyValue | None = None
    population_frequencies: list[PopulationFrequency] = Field(
        default_factory=list,
        description="Per-panel frequencies; always interpret with population_name.",
    )
    prediction_results: list[PredictionResult] = Field(
        default_factory=list,
        description="Allele-level predictions, currently including CADD.",
    )
    ensembl_website_display_data: VariantAlleleDisplayData | None = None
    phenotype_assertions: list[PhenotypeAssertion] | None = Field(
        default=None,
        description="Full-response phenotype associations; null for compact responses.",
    )
    predicted_molecular_consequences: list[MolecularConsequence] | None = Field(
        default=None,
        description="Full-response transcript consequences; null for compact responses.",
    )


class VariantDisplayData(VariantResponseModel):
    """Variant-level display summary."""

    count_citations: int | None = None


class VariantAnnotation(VariantResponseModel):
    """Typed short-variant annotation returned by Ensembl variation GraphQL."""

    name: str = Field(description="Primary variant name, normally an rsID.")
    alternative_names: list[ExternalReference] = Field(default_factory=list)
    type: str | None = None
    allele_type: OntologyValue | None = None
    primary_source: ExternalReference | None = None
    slice: VariantSlice | None = None
    prediction_results: list[PredictionResult] = Field(
        default_factory=list,
        description="Variant-level Ensembl VEP, GERP, and AncestralAllele results.",
    )
    alleles: list[VariantAllele] = Field(default_factory=list)
    ensembl_website_display_data: VariantDisplayData | None = None


class VariantIdInput(BaseModel):
    """Input for a variation GraphQL lookup."""

    genome_id: str
    variant_id: str = Field(
        description="Coordinate variant id in region:position:rsid form."
    )


def normalize_coordinate(value: str) -> str:
    """Normalize an exact coordinate to ``region:position`` for Ensembl REST."""
    normalized = value.strip()
    match = re.fullmatch(r"(?:chr)?([^:\s]+):([1-9][0-9]*)", normalized, re.IGNORECASE)
    if match is None:
        raise ValueError(
            f"Invalid coordinate: {value!r}; expected region:position, e.g. 1:230710048"
        )
    return f"{match.group(1)}:{match.group(2)}"


class RsidMapping(BaseModel):
    """One assembly mapping returned by the legacy Ensembl variation REST API."""

    seq_region_name: str
    start: int
    end: int
    assembly_name: str
    allele_string: str | None = None
    strand: int | None = None
    location: str | None = None

    def variant_id(self, rsid: str) -> str:
        """Build the coordinate identifier required by variation GraphQL."""
        return f"{self.seq_region_name}:{self.start}:{normalize_rsid(rsid)}"


class RsidResolution(BaseModel):
    """Assembly-filtered coordinate mappings for one rsID."""

    rsid: str
    species: str
    assembly: str
    mappings: list[RsidMapping]
    variant_ids: list[str] = Field(
        default_factory=list,
        description="Coordinate IDs accepted by variation GraphQL.",
    )


class VariantLookupResult(VariantResponseModel):
    """Bare-rsID resolution plus annotation for every assembly mapping."""

    resolution: RsidResolution
    variants: list[VariantAnnotation]


class MissingVariantResult(VariantResponseModel):
    """An rsID that could not be resolved or annotated."""

    rsid: str
    reason: str


class BatchVariantLookupResult(VariantResponseModel):
    """Per-item outcomes from compact batch rsID annotation."""

    found: list[VariantLookupResult]
    missing: list[MissingVariantResult]


def normalize_rsid(value: str) -> str:
    """Normalize a numeric or prefixed dbSNP identifier to lowercase ``rs...``."""
    normalized = value.strip().lower()
    if normalized.isdigit():
        normalized = f"rs{normalized}"
    if not re.fullmatch(r"rs[1-9][0-9]*", normalized):
        raise ValueError(f"Invalid rsID: {value!r}")
    return normalized


class RsidInput(BaseModel):
    """Validated rsID input used by MCP operations."""

    rsid: str

    @field_validator("rsid")
    @classmethod
    def validate_rsid(cls, value: str) -> str:
        return normalize_rsid(value)
