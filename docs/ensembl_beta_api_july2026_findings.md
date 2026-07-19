# Ensembl Beta API: July 2026 Exploration Findings

Investigation of all public API surfaces on `beta.ensembl.org`, with emphasis
on variant/SNP support, rsID resolution, and June-July 2026 changes.

Tested live on 2026-07-18.

## TL;DR

- **SNP queries work** via the variation GraphQL at `/api/graphql/variation` --
  but require coordinate-format IDs (`chr:pos:rsid`), not bare rsIDs.
- **No rsID resolver** exists on the beta platform. Use the old REST API
  (`rest.ensembl.org`) to map rsIDs to coordinates first.
- **AlphaMissense / ESM1b** scores were added to the **website UI** in June 2026
  but are **not yet in the variation GraphQL API** -- only CADD, SIFT, SpliceAI,
  GERP, and VEP are served.
- **Compara GraphQL** is live at `/api/graphql/compara` but returns **no data**
  for any gene tested (TP53, BRCA2, BRAF). Possibly no homology data loaded for
  the current release.
- **Core GraphQL** has had **no changes** to its root query fields in June-July.
- The **official help articles** still do not document the variation or compara
  endpoints.

---

## 1. API Versions (live as of 2026-07-18)

| Endpoint | Path | Version |
|---|---|---|
| Core GraphQL | `/data/graphql/core` | 0.2.0-beta |
| Variation GraphQL | `/api/graphql/variation` | 0.1.0-beta |
| Compara GraphQL | `/api/graphql/compara` | 0.2.beta-2 |

---

## 2. Variation GraphQL -- SNP Queries

### Endpoint

```
POST https://beta.ensembl.org/api/graphql/variation
Content-Type: application/json
```

Introspection **is enabled** on this endpoint.

### Root query fields

- `version` -- API version
- `variant(by_id: IdInput!)` -- look up a single variant
- `populations(genome_id: String!)` -- list available populations

### Variant ID format

Lookups require `genome_id` (UUID) plus a **coordinate-style** `variant_id`:

```
{chromosome}:{position}:{rsid}
```

**Bare rsIDs (`rs699`) fail** with error code `VARIANT_ID_NOT_FOUND`.

### Working example: rs699 (AGT missense, human GRCh38)

```graphql
query {
  variant(
    by_id: {
      genome_id: "a7335667-93e7-11ec-a39d-005056b38ce3"
      variant_id: "1:230710048:rs699"
    }
  ) {
    name
    allele_type { accession_id value }
    primary_source { name url description }
    slice {
      region { name }
      location { start end }
    }
    alleles {
      name
      allele_sequence
      reference_sequence
      allele_type { accession_id value }
      population_frequencies {
        population_name
        allele_frequency
        is_minor_allele
      }
      predicted_molecular_consequences {
        stable_id
        feature_type { accession_id value }
        consequences { accession_id value }
        gene_stable_id
        gene_symbol
        prediction_results {
          score
          classification { value }
          analysis_method { tool version }
        }
      }
    }
    prediction_results {
      score
      classification { accession_id value }
      analysis_method { tool version }
    }
    ensembl_website_display_data { count_citations }
  }
}
```

#### Result summary for rs699

| Field | Value |
|---|---|
| name | rs699 |
| allele_type | SNV |
| primary_source | NCBI db of human variants |
| location | chr1:230710048 |
| alleles | A (ref), G (alt, missense in AGT) |
| gnomAD exomes v4.1 global MAF | 0.458 (G allele) |
| gnomAD genomes v4.1 global AF | 0.578 (G allele) |
| variant-level predictions | VEP, GERP (-2.97), AncestralAllele |
| per-allele predictions | CADD (at allele level) |
| per-consequence predictions | SIFT (per transcript), SpliceAI (per transcript) |
| gene affected | AGT (ENSG00000135744) |
| consequences | missense_variant, NMD_transcript_variant |

### Working example: rs28934578 (TP53 R175H hotspot)

```graphql
query {
  variant(
    by_id: {
      genome_id: "a7335667-93e7-11ec-a39d-005056b38ce3"
      variant_id: "17:7675088:rs28934578"
    }
  ) {
    name
    alleles {
      name
      allele_sequence
      prediction_results {
        score
        analysis_method { tool }
      }
      predicted_molecular_consequences {
        gene_symbol
        consequences { value }
        prediction_results {
          score
          classification { value }
          analysis_method { tool version }
        }
      }
    }
  }
}
```

Result: CADD=28.0 (allele-level), SIFT=0.0 (deleterious), multiple SpliceAI
delta scores per transcript.

### Prediction tools available in the API

| Tool | Level | Score range | Notes |
|---|---|---|---|
| CADD | per allele | 0-99 (phred) | Present |
| SIFT | per consequence | 0-1 (lower = more damaging) | Present |
| SpliceAI | per consequence | multiple delta scores per transcript | Present, 8 values per consequence |
| GERP | per variant | negative to ~6 | Present |
| Ensembl VEP | per variant | -- | Present (no score, flag only) |
| AncestralAllele | per variant | -- | Present (v110) |
| **AlphaMissense** | -- | -- | **NOT in API** (UI only, added June 2026) |
| **ESM1b** | -- | -- | **NOT in API** (UI only, added June 2026) |
| PolyPhen | per consequence | 0-1 (higher = more damaging) | Observed live for some rs699 consequences |

### Available populations

52 populations served for human GRCh38:

- **1000 Genomes Phase 3**: 31 populations (ALL + 5 superpopulations + 26 subpopulations)
- **gnomAD exomes v4.1**: 10 populations (ALL + 9 ancestry groups)
- **gnomAD genomes v4.1**: 11 populations (ALL + 10 ancestry groups including Amish)

Note: the `populations` query has upstream nullability bugs. Both `size` and
`is_from_genotypes` are declared non-nullable but can return null, causing list
entries to become null when either field is requested. Omit both as a workaround.

### Full variation schema types

```
Variant: name, alternative_names, primary_source, type, allele_type, slice,
         alleles, prediction_results, ensembl_website_display_data

VariantAllele: name, allele_sequence, reference_sequence, alternative_names,
               type, allele_type, slice, phenotype_assertions, prediction_results,
               population_frequencies, predicted_molecular_consequences,
               ensembl_website_display_data

PredictedMolecularConsequence: allele_name, stable_id, feature_type, consequences,
                                prediction_results, gene_stable_id, gene_symbol,
                                protein_stable_id, transcript_biotype, cdna_location,
                                cds_location, protein_location

PredictionResult: score, result, classification, analysis_method
AnalysisMethod: tool, version, qualifier, reference_data
Population: name, size*, description, type, is_global, is_from_genotypes,
            display_group_name, super_population, sub_populations
PopulationAlleleFrequency: population_name, allele_frequency, allele_count,
                           allele_number, is_minor_allele, is_hpmaf
PhenotypeAssertion: feature, feature_type, phenotype, evidence
VariantDisplayData: count_citations
VariantAlleleDisplayData: count_transcript_consequences, count_overlapped_genes,
                          count_regulatory_consequences, count_variant_phenotypes,
                          count_gene_phenotypes, representative_population_allele_frequency
```

*`size` is buggy -- returns null despite non-nullable declaration.

---

## 3. Resolving rsIDs to Coordinates

The beta variation API requires `chr:pos:rsid` format. There is **no rsID-only
resolver** on the beta platform. Options for resolving bare rsIDs:

### Option A: Old Ensembl REST API (works today)

```bash
curl -s 'https://rest.ensembl.org/variation/human/rs699?content-type=application/json'
```

Returns mappings with coordinates:

```json
{
  "name": "rs699",
  "mappings": [{
    "seq_region_name": "1",
    "start": 230710048,
    "end": 230710048,
    "assembly_name": "GRCh38",
    "allele_string": "A/G"
  }]
}
```

Then construct the variant_id: `1:230710048:rs699`

### Option B: NCBI dbSNP API

```bash
curl -s 'https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/699'
```

### Option C: No direct beta API path

The Ensembl Resolver API (`resolver.ensembl.org`) resolves stable IDs (genes,
transcripts) to URLs, but does **not** handle rsIDs or variant lookups.

---

## 4. Compara GraphQL -- Homologies

### Endpoint

```
POST https://beta.ensembl.org/api/graphql/compara
Content-Type: application/json
```

Introspection is **disabled**.

### Schema (reverse-engineered from ensembl-client source and probing)

```graphql
query {
  homologies(genome_id: String!, gene_stable_id: String!) {
    type
    subtype { accession_id label value definition }
    query_genome {
      genome_id
      common_name
      scientific_name
      assembly { accession_id name }
    }
    query_gene {
      stable_id
      symbol
      version
      unversioned_stable_id
    }
    target_genome {
      genome_id
      common_name
      scientific_name
      assembly { accession_id name }
    }
    target_gene {
      stable_id
      symbol
      version
      unversioned_stable_id
    }
    stats {
      query_percent_id
      query_percent_coverage
      target_percent_id
      target_percent_coverage
    }
  }
}
```

### Current status: returns empty results

Tested with BRCA2 (`ENSG00000139618`), TP53 (`ENSG00000141510`), BRAF
(`ENSG00000157764`) -- all return `{"data": {"homologies": []}}` (empty array,
not null). This means the compara pipelines have been run but found no homologies,
which is implausible for these genes. Likely a data loading issue with the
current partial release.

The ensembl-client source notes that `null` means "pipelines not run" while
`[]` means "run but no homologies found."

---

## 5. Core GraphQL -- No Changes

Root fields unchanged (verified via introspection):

```
version, gene, genes, transcript, transcript_search, product,
overlap_region, region, genomes, genome
```

No variant or SNP fields. `transcript_search` was added around March 2026
(pre-existing before this investigation window).

---

## 6. Help Articles Status

Both help articles the Ensembl website links to are React SPA pages that
cannot be fetched programmatically (client-side rendered). Their documented
content as of July 2026:

| Article | Documents | Missing |
|---|---|---|
| [GraphQL services](https://beta.ensembl.org/help/articles/getting-started-with-ensembl-graph-ql-services) | `/data/graphql` (core only) | variation, compara endpoints |
| [Refget services](https://beta.ensembl.org/help/articles/accessing-ensembl-s-refget-services) | `/data/refget/` | `/api/refget` path |

---

## 7. June-July 2026 Changes Summary

### API-relevant

- **AlphaMissense + ESM1b** pathogenicity scores added to website variant pages
  (June 25), replacing MutationAssessor and MetaLR. Sourced from dbNSFP v5.2c.
  **Not yet in GraphQL variation API.**
- **Partial releases** continued: 2026-06-07, 2026-06-25, 2026-07-08, 2026-07-13
- **Ensembl 116** released June 9 -- the **final release on the old platform**.
  New data now goes exclusively to the new platform.

### Platform/UI only

- App renames (July 14): Entity viewer -> Feature Explorer, Species selector ->
  Genome selector. Old URLs redirect.
- FTP reorganization (June 26): files now under `GCA/`/`GCF/` by assembly
  accession. Old species-name layout retiring August 2026.
- MySQL 8 upgrade (June 2): public MySQL servers upgrading from 5.6 to 8.
  No schema changes; GraphQL/Refget APIs unaffected.
- New structural variant alignment viewer (May 2026, UI only).

### Upstream repos

- **ensembl-hypsipyle** (variation GraphQL): population metadata updates (wheat
  MAGIC-16, PR #68 merged June 3). Structural variant GraphQL (PR #65) still
  open as of July 16.
- **ensembl-thoas** (core GraphQL): wheat cross-reference URL fix (June).
  No new root query fields.

---

## 8. What ensembl-mcp Added in 0.3.0

The actionable surfaces from this investigation are now wrapped:

| Backend | Status | Actionable? |
|---|---|---|
| Variation GraphQL | Live, introspectable, returns rich data | Wrapped |
| Compara GraphQL | Live but returns empty data | Wrapped with the upstream limitation documented |
| rsID resolver | Not on beta; old REST API works | Wrapped as single/batch resolution and annotation |
| AlphaMissense/ESM1b | UI only | Not yet -- monitor for GraphQL addition |
| Metadata API | `/api/metadata/releases` works | Wrapped |
| Search API | `/api/search` | Unexplored |

### Suggested rsID resolution workflow

```
1. User provides: rs699
2. ensembl-mcp calls rest.ensembl.org:
   GET /variation/human/rs699 -> chr1:230710048, alleles A/G
3. ensembl-mcp calls beta.ensembl.org variation GraphQL:
   variant(variant_id: "1:230710048:rs699") -> full annotation
4. Return: frequencies, consequences, predictions
```

---

## Appendix: curl One-Liners

### Query a variant by coordinate-format ID

```bash
curl -s 'https://beta.ensembl.org/api/graphql/variation' \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ variant(by_id: { genome_id: \"a7335667-93e7-11ec-a39d-005056b38ce3\", variant_id: \"1:230710048:rs699\" }) { name allele_type { value } alleles { name allele_sequence population_frequencies { population_name allele_frequency } } } }"}'
```

### Resolve rsID via old REST API

```bash
curl -s 'https://rest.ensembl.org/variation/human/rs699?content-type=application/json' \
  | jq '.mappings[] | "\(.seq_region_name):\(.start):\(.name // empty)"'
```

### List populations

```bash
curl -s 'https://beta.ensembl.org/api/graphql/variation' \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ populations(genome_id: \"a7335667-93e7-11ec-a39d-005056b38ce3\") { name description type is_global display_group_name } }"}'
```

### Full introspection of variation schema

```bash
curl -s 'https://beta.ensembl.org/api/graphql/variation' \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ __schema { types { name kind fields { name type { name kind ofType { name } } } } } }"}'
```
