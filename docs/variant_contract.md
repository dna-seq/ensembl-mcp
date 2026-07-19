# Variant Response Contract

The variant tools publish Pydantic output schemas through MCP, including field
descriptions. `get_variant` returns a `VariantAnnotation`;
`get_variant_by_rsid` returns `resolution` plus one annotation for every assembly
mapping. Do not silently choose the first mapping when more than one is returned.

## Annotation structure

Useful paths in a full annotation:

- `slice.region.name`, `slice.location`, `slice.strand`: genomic placement.
- `allele_type.value`: SNV/indel classification (`type` is currently the generic
  value `Variant`).
- `alleles[]`: one record per reference or alternate allele. Use
  `reference_sequence` and `allele_sequence`; do not assume the first item is the
  only alternate at a multiallelic site.
- `alleles[].population_frequencies[]`: frequency, allele count/number, and minor
  allele flags. Always report the exact `population_name`; counts can be null for
  inferred reference alleles.
- `alleles[].phenotype_assertions[]`: phenotype name, source, ontology terms, and
  supporting evidence. These are sourced associations, not diagnoses.
- `alleles[].predicted_molecular_consequences[]`: affected gene, transcript,
  protein, biotype, Sequence Ontology terms, and cDNA/CDS/protein coordinates.

## Prediction result scoping

Prediction scope matters: variant `prediction_results` contain Ensembl
VEP, GERP, and AncestralAllele; allele results contain CADD; molecular
consequence results contain SIFT, SpliceAI, and currently PolyPhen.
Scores from different methods are not interchangeable. SpliceAI currently
arrives as multiple raw results per transcript, so do not invent delta-score
labels absent from the API.

## Compact mode

With `full=False`, identity, placement, alleles, frequencies, display summaries,
and variant/allele predictions remain, while phenotype assertions and molecular
consequences are omitted. Use `get_variant_to_file` when a full annotation is too
large for model context.

## Clinical summary

`get_variant_clinical_summary` distills a full annotation into:
- Variant-level predictions (VEP, GERP, AncestralAllele)
- Per-allele CADD scores
- Filtered population frequencies (default: gnomADe:ALL, gnomADg:ALL,
  1000GENOMES:phase_3:ALL; or custom `populations` list)
- Per-consequence SIFT, PolyPhen, and max SpliceAI delta scores
- Phenotype associations with source attribution

## Reference variants

Live examples used by the integration suite:

- `1:230710048:rs699`: A reference and G alternate, AGT consequences, gnomAD
  population frequencies, CADD at allele level, and GERP/VEP at variant level.
- `17:7675088:rs28934578`: multiallelic TP53 hotspot with transcript-level
  consequences and prediction results; some alleles have no population records.
