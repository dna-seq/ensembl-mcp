# Ensembl beta backends (as of 2026-07)

Ensembl’s public help articles describe “the GraphQL service” as a single URL.
The beta website actually talks to **several backends**. This note records what
is live on `beta.ensembl.org`, how the official docs map (or fail to map) onto
that surface, and what `ensembl-mcp` currently wraps.

Verified by live introspection and queries on 2026-07-18 against
[Beta Release 2025-02](https://beta.ensembl.org/) (integrated) with current
partial release `2026-07-13`.

## Official docs vs reality

| Help article | Documented URL | Accurate? |
|---|---|---|
| [Accessing Ensembl GraphQL services](https://beta.ensembl.org/help/articles/getting-started-with-ensembl-graph-ql-services) | `https://beta.ensembl.org/data/graphql` | Partial — this is **core only** |
| [Accessing Ensembl's refget services](https://beta.ensembl.org/help/articles/accessing-ensembl-s-refget-services) | `https://beta.ensembl.org/data/refget/` | Yes for Refget; does not mention `/api/refget` |

Neither article documents variation or compara GraphQL.

## Backends the website uses

Paths below come from
[`ensembl-client` `config.ts`](https://github.com/Ensembl/ensembl-client/blob/main/config.ts)
(`defaultApiUrls`) and were checked live.

| Client config key | Public path | Role | Upstream project | API version (live) |
|---|---|---|---|---|
| `coreApiUrl` | `/api/graphql/core` | Genes, transcripts, products, regions, genomes | [ensembl-thoas](https://github.com/Ensembl/ensembl-thoas) | `0.2.0-beta` |
| `variationApiUrl` | `/api/graphql/variation` | Short variants / SNPs | [ensembl-hypsipyle](https://github.com/Ensembl/ensembl-hypsipyle) | `0.1.0-beta` |
| `comparaApiBaseUrl` | `/api/graphql/compara` | Homologies / compara | (compara GraphQL) | `0.2.beta-2` |
| `refgetBaseUrl` | `/api/refget` | GA4GH Refget sequences | Refget server | — |
| `metadataApiBaseUrl` | `/api/metadata` | Releases, genome groups, etc. | metadata REST | — |
| `searchApiBaseUrl` | `/api/search` | Site search | search REST | — |
| `toolsApiBaseUrl` | `/api/tools` | BLAST / VEP job APIs | tools REST | — |
| `structuralVariantsApiBaseUrl` | `/api/sv-alignments` | Alignments / SV viewer data | SV alignments | — |
| `regulationApiBaseUrl` | `https://regulation.ensembl.org/api` | Regulation / epigenomes | regulation site | — |

### `/data/...` vs `/api/...`

Both prefixes are served on `beta.ensembl.org`:

- **`/data/graphql`** and **`/data/graphql/core`** — public GraphiQL + core schema.
  This is what the [GraphQL help article](https://beta.ensembl.org/help/articles/getting-started-with-ensembl-graph-ql-services)
  documents and what `ensembl-mcp` uses by default.
- **`/api/graphql/core`** — same core backend the website prefers; introspection is
  disabled on this path.
- **`/api/graphql/variation`** — live variation GraphQL (hypsipyle). **Not** the same
  as `/data/graphql/variation`, which currently returns the **core** schema
  (misleading path).
- **`/data/refget`** and **`/api/refget`** — same Refget service under two prefixes.
  Docs and `ensembl-mcp` use `/data/refget`.

Prefer the path that matches the intended backend. Do not assume every
`/data/graphql/<name>` is a distinct schema.

## Core GraphQL (Thoas)

- Endpoint (docs / MCP default): `https://beta.ensembl.org/data/graphql/core`
- Root fields: `version`, `gene`, `genes`, `transcript`, `transcript_search`,
  `product`, `overlap_region`, `region`, `genomes`, `genome`
- No `variant` field

## Variation GraphQL (Hypsipyle) — SNPs are live

- Endpoint: `https://beta.ensembl.org/api/graphql/variation`
- Root fields: `version`, `variant`, `populations`
- Schema includes alleles, population frequencies (e.g. gnomAD), prediction
  results (VEP/CADD-style), predicted molecular consequences, phenotype
  assertions, website display helpers
- Wrapped by `get_variant`, `get_variant_by_rsid`, `batch_get_variants_by_rsid`,
  `batch_resolve_coordinates`, `list_variant_populations`, and
  `get_variant_to_file`.

### Variant ID format

Lookups take `genome_id` (UUID) plus a **coordinate-style** `variant_id`:

```text
{region}:{position}:{rsid}
```

Examples that work:

- `1:230710048:rs699`
- `1:10153:rs1639547929`

Bare rsIDs (`rs699`) fail with `VARIANT_ID_NOT_FOUND`. There is no documented
rsid-only resolver on this endpoint. `ensembl-mcp` bridges this gap through the
legacy Ensembl REST variation endpoint and retains every mapping for the requested
assembly rather than silently selecting an ambiguous placement.

Minimal live query:

```graphql
query {
  variant(
    by_id: {
      genome_id: "a7335667-93e7-11ec-a39d-005056b38ce3"
      variant_id: "1:230710048:rs699"
    }
  ) {
    name
    slice { region { name } location { start end } }
    alleles { name allele_sequence reference_sequence }
  }
}
```

GraphiQL: open `https://beta.ensembl.org/api/graphql/variation` in a browser.

### Not shipped yet

- Structural-variant GraphQL support is in progress upstream
  ([ensembl-hypsipyle PR #65](https://github.com/Ensembl/ensembl-hypsipyle/pull/65),
  still open as of 2026-07-16). The Alignments / SV **UI** exists; the variation
  GraphQL root does not yet expose a general SV query surface.

## Compara GraphQL

- Endpoint: `https://beta.ensembl.org/api/graphql/compara`
- At least a `homologies` field (requires `genome_id` + `gene_stable_id`)
- Introspection disabled; not wrapped by `ensembl-mcp`

## Refget

Documented and working:

- Base: `https://beta.ensembl.org/data/refget/`
- Sequence: `/sequence/{id}` (`Accept: text/plain`)
- Metadata: `/sequence/{id}/metadata` (`Accept: application/json`)
- Coordinates are **0-based, half-open** (convert from Ensembl 1-based by
  subtracting 1 from start)

See also [Architecture and Refget Integration](./refget_and_architecture.md).

## Releases (metadata API)

`GET https://beta.ensembl.org/api/metadata/releases` (2026-07-18):

- Current **integrated**: `2025-02` (matches the site banner)
- Current **partial**: `2026-07-13`
- Recent partials include `2026-06-07`, `2026-06-25`, `2026-07-08`, `2026-07-13`

## June–July 2026 changes (relevant to APIs)

Mostly platform/UI/FTP, not a new core SNP field:

- App renames (Entity viewer → Feature explorer; Species selector → Genome selector)
- New Ensembl FTP layout under `GCA/` / `GCF/` (species-name layout retiring)
- Ensembl 116 final legacy release (2026-06-09); new data goes to the new platform
- AlphaMissense + ESM1b pathogenicity scores added to website UI (2026-06-25),
  replacing MutationAssessor and MetaLR. **Not in GraphQL API yet** -- only
  CADD, SIFT, SpliceAI, GERP, VEP are served via `/api/graphql/variation`
- Hypsipyle: population-metadata updates (e.g. wheat MAGIC-16); SV GraphQL still open
- MySQL 8 upgrade announced (2026-06-02); no schema changes
- Variation GraphQL itself was already wired into the beta client years earlier;
  what was missing was accurate public documentation of `/api/graphql/variation`
- Partial releases: 2026-06-07, 2026-06-25, 2026-07-08, 2026-07-13

See [ensembl_beta_api_july2026_findings.md](./ensembl_beta_api_july2026_findings.md)
for detailed exploration with working query examples.

## What `ensembl-mcp` wraps today

| Backend | Wrapped? |
|---|---|
| Core GraphQL (`/data/graphql/core`) | Yes |
| Refget (`/data/refget`) | Yes |
| Variation GraphQL (`/api/graphql/variation`) | Yes |
| Legacy REST variation rsID resolution | Yes |
| Compara GraphQL | Yes (upstream currently returns empty lists) |
| Metadata releases | Yes |
| Search / tools / SV alignments / regulation | No |

Population queries omit both `size` and `is_from_genotypes`: both are declared
non-nullable upstream but currently resolve to null and null the affected list
entries. Structural variants and UI-only prediction methods remain out of scope
until their upstream APIs are available.
