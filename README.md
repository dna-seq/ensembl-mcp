<div align="center">

# 🧬 Ensembl for AI genomics

### A standalone MCP server, Claude plugin, and Codex plugin for live Ensembl genomics.

**Genes · variants · transcripts · proteins · phenotypes · population frequencies · sequences**

[![PyPI](https://img.shields.io/pypi/v/ensembl-mcp?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/ensembl-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/ensembl-mcp?logo=python&logoColor=white)](https://pypi.org/project/ensembl-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-standalone-5A45FF)](#run-it-as-a-standalone-mcp-server)
[![Claude Plugin](https://img.shields.io/badge/Claude-plugin-D97757?logo=anthropic&logoColor=white)](#get-the-claude-plugin)
[![Codex Plugin](https://img.shields.io/badge/Codex-plugin-412991?logo=openai&logoColor=white)](#install-the-codex-plugin)

**Standalone MCP · Claude plugin · Codex plugin · 10 genomics skills · No Ensembl API key**

</div>

`ensembl-mcp` is a portable live [Ensembl](https://ensembl.org) toolkit. Run it
as a standard MCP server from any compatible client, or install the Claude and
Codex plugins to get the server *plus* focused genomics workflows for gene
lookup, transcripts, clinical variants, regions, proteins, sequences, species,
and variant conversion.

### One genomics backend. Three ways to use it.

| Use it as… | You get… |
| --- | --- |
| 🔌 **Standalone MCP server** | Live Ensembl tools over stdio or streamable HTTP for any compatible agent |
| 🟠 **Claude plugin** | The server plus 10 skills for Claude Code; the server also works in Desktop and Cowork |
| ⚫ **Codex plugin** | The same server and skills, installable through Codex’s Plugins Directory |

```text
You ask your AI agent
      ↓
The agent—or a bundled plugin skill—selects the lookup workflow
      ↓
ensembl-mcp queries live Ensembl services
      ↓
You get a sourced, structured answer
```

## See it answer real genomics questions

Every answer below came from a live Ensembl query—not a model’s recollection.

<details open>
<summary><strong>🧬 “Tell me about BRCA2.”</strong></summary>

| | |
| --- | --- |
| **Ensembl ID** | ENSG00000139618.18 |
| **Full name** | BRCA2 DNA repair associated |
| **Location** | Chromosome 13 : 32,315,086 -- 32,400,268 |
| **MANE Select** | ENST00000380152.8 |
| **Also known as** | FANCD1, FANCD, FACD, BRCC2 |
| **Cross-references** | HGNC, OMIM, UniProt, RefSeq, Reactome, Expression Atlas, GeneCards |

</details>

<details open>
<summary><strong>💊 “What is rs699? Is it pathogenic? What are its population frequencies?”</strong></summary>

| | |
| --- | --- |
| **Location** | chr1:230,710,048 (SNV) |
| **Gene / consequence** | AGT · missense_variant (p.Met259Thr) |
| **gnomADe:ALL** | 0.458 (minor allele: G) |
| **gnomADg:ALL** | 0.578 |
| **CADD / SIFT / PolyPhen** | 0.09 · 1.0 (tolerated) · 0.0 (benign) |
| **Phenotype associations** | Hypertension, preeclampsia, renal tubular dysgenesis, and more |

</details>

<details>
<summary><strong>🏥 “What do we know about the TP53 R175H mutation (rs28934578)?”</strong></summary>

| | |
| --- | --- |
| **Location** | chr17:7,675,088 (multiallelic: C>A/G/T) |
| **Consequence** | missense_variant, p.Arg175His |
| **GERP / SIFT / SpliceAI** | 3.36 · 0.0 (deleterious) · max delta 0.01 |
| **Phenotype associations** | Li-Fraumeni syndrome, breast neoplasm, colorectal cancer, and more |

</details>

## Get the Claude plugin

### ⚡ Claude Code

```bash
git clone https://github.com/dna-seq/ensembl-mcp.git
claude --plugin-dir ./ensembl-mcp
```

One install gives Claude the plugin’s skills and its preconfigured, pinned Ensembl
MCP server. Ask: **“Tell me about BRCA2 and identify its MANE Select
transcript.”**

### 💼 Claude Desktop and Cowork

Add the standard Claude Desktop MCP configuration from the
[client setup guide](docs/client_setup.md#claude-desktop-and-cowork). Claude Cowork reuses
those local MCP servers, so the Ensembl tools are available in Cowork sessions
after the desktop configuration is connected.

### 📦 Build a portable plugin archive

Build the small, metadata-only ZIP for a Claude client that accepts plugin
uploads:

```bash
cd ensembl-mcp
uv run pack plugin
```

The generated ZIP launches the published server through `uvx`; it does not bundle
the repository or a database.

## The same genomics toolkit beyond Claude

The plugin is the primary Claude experience. Its MCP server remains intentionally
portable, so the same live Ensembl tools also work in:

| Client or workflow | What you reuse |
| --- | --- |
| ⚫ **Codex / ChatGPT** | A native Codex plugin that bundles the same skills and Ensembl MCP tools |
| 🔵 **Google Antigravity** | The same local stdio server through its MCP Servers panel |
| 🤖 **Custom autonomous agents** | Standard MCP over stdio or streamable HTTP, typed responses, and background tasks |
| 🖥️ **Cursor, Cline, and other MCP clients** | The same `uvx`-launched server |

## Install the Codex plugin

The native Codex plugin reuses the genomics skills and pinned server configuration
from this repository. Add the DNA-Seq plugin marketplace:

```bash
codex plugin marketplace add dna-seq/ensembl-mcp
```

In Codex, run `/plugins`, choose **DNA-Seq Plugins**, and install
**Ensembl: Genes, Variants, and Sequences**. The plugin provides both the
Ensembl tools and the matching genomics workflows.

For a bare-server setup instead, use
`codex mcp add ensembl -- uvx ensembl-mcp serve`. See
[Codex setup](docs/client_setup.md#codex-cli-chatgpt-desktop-and-the-codex-ide-extension)
for details.

## Add it to Antigravity

In Antigravity, open the Agent panel’s **⋯** menu, choose **MCP Servers** →
**Manage MCP Servers** → **View raw config**, then add:

```json
{
  "mcpServers": {
    "ensembl": {
      "command": "uvx",
      "args": ["ensembl-mcp", "serve"]
    }
  }
}
```

Save the configuration and confirm the server is connected in the MCP Servers
panel. If Antigravity cannot locate `uvx`, replace `"uvx"` with the absolute
path printed by `which uvx`. Full instructions are in the
[client setup guide](docs/client_setup.md#google-antigravity).

## Run it as a standalone MCP server

Use `uvx ensembl-mcp serve` as a standard MCP **stdio** server in any compatible
client, or run `uvx ensembl-mcp serve --transport http --port 8000` for a
streamable HTTP endpoint. The tool surface is client-neutral: typed responses,
bulk operations, file exports for large results, and MCP background tasks work
whether an engineer or an autonomous agent calls them.

## Why not use an unconnected LLM?

Claude, Codex, and other LLMs can explain what an rsID or MANE Select transcript
*is*, but their training data is not a live genomics database. Without tools,
they may:

- 🧭 mix GRCh37 and GRCh38 coordinates;
- 🧪 omit alleles at multiallelic sites or flatten prediction scopes;
- 🗓️ answer from stale releases and population datasets;
- 🎭 confidently invent an identifier, transcript, consequence, or citation.

That distinction matters: fluent biological reasoning is useful, but it cannot
replace exact database retrieval. `ensembl-mcp` combines both—the LLM plans and
explains; Ensembl supplies the current records. This is especially important
when an answer feeds a script, report, PRS workflow, or downstream clinical
review. See [Validation in Agentic Workflows](docs/validation.md) for concrete
failure modes.

## Who saves time with this?

- 🔬 **Bioinformaticians** — inspect unfamiliar loci, resolve batches of rsIDs,
  check transcript consequences, and bridge products to Refget without writing
  a throwaway client for every question.
- 🧫 **Biologists** — move from a gene symbol to transcripts, exons, domains,
  pathways, phenotypes, and cross-references in one conversation.
- 🧑‍💻 **Citizen scientists** — ask plain-language questions while keeping the
  identifiers, coordinates, populations, and prediction sources visible.
- 🤖 **Agent builders** — add typed genomics tools, structured output, file
  exports, and background-task support to pipelines without maintaining an
  Ensembl integration.

> **Use it for research and exploration, not as a substitute for clinical
> interpretation or medical advice.**

---

## More live questions

The same server and plugins also handle transcript structure, sequences, protein
domains, variant formats, disease associations, regions, populations, and batch
identifier resolution.

<details>
<summary><strong>:test_tube: "How many exons does the canonical BRCA2 transcript have?"</strong></summary>

| | |
| --- | --- |
| **Transcript** | ENST00000380152.8 (BRCA2-201) |
| **MANE Select** | Yes (RefSeq NM_000059.4) |
| **Canonical** | Yes |
| **APPRIS** | principal2 |
| **Exons** | 27 (chr13:32,315,508 -- 32,400,268) |
| **CDS** | 10,257 nt encoding 3,418 aa |
| **Protein** | ENSP00000369497.3 |

</details>

<details>
<summary><strong>:crystal_ball: "Give me the amino acid sequence of TP53."</strong></summary>

```
Gene:       TP53
Transcript: ENST00000269305.9 (MANE Select, canonical, NM_000546.6)
Product:    ENSP00000269305.4
Length:     393 aa
Sequence:   MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAM...
```

Bridges gene symbol -> canonical transcript -> product checksum -> Refget
sequence in a single call. Also works with a product ID directly.

</details>

<details>
<summary><strong>:jigsaw: "What domains does the TP53 protein have?"</strong></summary>

| Domain (Pfam) | Position |
| --- | --- |
| PF08563 (P53 TAD) | 6 -- 30 |
| PF18521 (P53 TAD2) | 35 -- 59 |
| PF00870 (P53 DNA-binding) | 100 -- 288 |
| PF07710 (P53 tetramerization) | 319 -- 357 |

Plus cross-references to PDB structures, UniProt/Swiss-Prot, Reactome pathways,
ChEMBL, Human Protein Atlas, BioGRID, and RefSeq.

</details>

<details>
<summary><strong>:twisted_rightwards_arrows: "Convert rs28934578 to HGVS notation."</strong></summary>

| Format | Value |
| --- | --- |
| **Genomic HGVS** | NC_000017.11:g.7675088C>T |
| **Coding HGVS** | ENST00000269305.9:c.524G>A |
| **Protein HGVS** | ENSP00000269305.4:p.Arg175His |
| **SPDI** | NC_000017.11:7675087:C:T |

Also converts from HGVS or SPDI input back to rsID and other formats.

</details>

<details>
<summary><strong>:microbe: "What diseases are associated with TP53?"</strong></summary>

**443 phenotype associations** from ClinVar, Cancer Gene Census, GWAS catalog,
OMIM, and other sources, including:

Li-Fraumeni syndrome, Gastric adenocarcinoma, Colorectal hamartoma, Pituitary
adenocarcinoma, Acinar lung adenocarcinoma, Brain stem astrocytic neoplasm,
Ethmoid sinus squamous cell carcinoma, and hundreds more.

</details>

<details>
<summary><strong>:world_map: "What clinically significant variants are in BRCA2 exon 11?"</strong></summary>

Scanning just 1 kb of BRCA2 (chr13:32,340,000-32,341,000) returns **1,655
variants**, of which **1,224** have clinical significance annotations:

| rsID | Consequence | Clinical significance |
| --- | --- | --- |
| rs1555284326 | frameshift_variant | pathogenic |
| rs80358785 | stop_gained | pathogenic, risk factor |
| rs2072528988 | inframe_deletion | uncertain significance |

Scale this to a full gene or an entire region of interest.

</details>

<details>
<summary><strong>:bar_chart: "How does rs699 frequency vary across populations?"</strong></summary>

| Population | Frequency | Minor allele? |
| --- | --- | --- |
| gnomADe:AFR | 0.847 | No |
| gnomADe:EAS | 0.825 | No |
| gnomADe:NFE | 0.410 | Yes |

Request any population panel by name -- use `list_variant_populations` to see
all available panels.

</details>

<details>
<summary><strong>:mag: "What gene is at position 143,351,678 on chromosome 7?"</strong></summary>

**CLCN1** (chloride voltage-gated channel 1), ENSG00000188037.14. Verified
live against the current GRCh38 assembly -- not guessed from training data.

</details>

<details>
<summary><strong>:package: "Resolve rs699, rs28934578, and rs55960271 to their chromosomes and alleles."</strong></summary>

| rsID | Chr | Position | Alleles |
| --- | --- | --- | --- |
| rs699 | 1 | 230,710,048 | A/G |
| rs28934578 | 17 | 7,675,088 | C/A/G/T |
| rs55960271 | 7 | 143,351,678 | C/A/T |

Batch operations support progress reporting and handle missing/invalid rsIDs
gracefully.

</details>

---

## Server transport options

Any MCP-compatible client can launch the server over stdio:

```bash
uvx ensembl-mcp serve
```

For multi-client or remote use, start streamable HTTP transport:

```bash
uvx ensembl-mcp serve --transport http --host 0.0.0.0 --port 8000
```

Then use the [client setup guide](docs/client_setup.md) for ready-to-paste
configurations. The same server works with Cursor, Cline, Codex, Antigravity,
custom agents, and programmatic MCP clients.

---

## Tools

<details open>
<summary><strong>Gene & Transcript</strong> (8 tools)</summary>

| Tool | What it does |
| --- | --- |
| `find_genes_by_symbol` | Look up a gene by name (BRCA2, TP53, EGFR...) with full metadata, xrefs, and transcript list |
| `get_gene_by_id` | Look up a gene by Ensembl stable ID |
| `get_transcript` | Transcript details: exons, CDS/UTR, MANE/canonical flags, linked protein |
| `transcript_search` | Search transcripts by identifier across genomes |
| `get_product_by_id` | Protein product: domains (Pfam, PANTHER), xrefs (PDB, UniProt), Refget checksum |
| `get_protein_sequence` | Amino acid sequence for a gene or product (bridges GraphQL to Refget) |
| `overlap_region` | Genes and transcripts overlapping a genomic interval |
| `bulk_find_genes` | Resolve many gene symbols at once (with progress reporting) |

</details>

<details>
<summary><strong>Variant & Clinical</strong> (11 tools)</summary>

| Tool | What it does |
| --- | --- |
| `get_variant` | Full variant annotation by `region:position:rsid` coordinate |
| `get_variant_by_rsid` | Resolve a bare rsID and annotate it (combines REST + GraphQL) |
| `get_variant_clinical_summary` | Compact clinical view: filtered frequencies, SIFT/PolyPhen/SpliceAI, phenotypes |
| `get_variants_in_region` | All known variants in a genomic interval with clinical significance |
| `get_gene_phenotypes` | Disease/phenotype associations (ClinVar, OMIM, GWAS, Cancer Gene Census) |
| `variant_recoder` | Convert between rsID, HGVS, SPDI, and VCF formats |
| `resolve_rsid` | Resolve one bare rsID to GRCh38 coordinates |
| `batch_resolve_rsids` | Resolve many rsIDs at once |
| `batch_get_variants_by_rsid` | Resolve and compactly annotate many rsIDs |
| `batch_resolve_coordinates` | Find variants at exact genomic positions |
| `list_variant_populations` | Available population panels for allele frequencies |

</details>

<details>
<summary><strong>Sequence & Reference</strong> (4 tools)</summary>

| Tool | What it does |
| --- | --- |
| `get_sequence` | Raw Refget sequence or subsequence by digest ID |
| `get_sequence_to_file` | Stream large sequences to a local file |
| `get_sequence_metadata` | Metadata and aliases for a sequence digest |
| `get_region` | Region (chromosome) metadata by name |

</details>

<details>
<summary><strong>Genome & Metadata</strong> (6 tools)</summary>

| Tool | What it does |
| --- | --- |
| `find_genomes` | Resolve species/assembly to genome(s) and genome_id |
| `get_genome` | Genome metadata by genome_id |
| `get_releases` | Ensembl beta release metadata |
| `get_version` | Core GraphQL API version |
| `get_variation_version` | Variation GraphQL API version |
| `get_homologies` | Compara homologies for a gene |

</details>

<details>
<summary><strong>Escape hatches</strong> (3 tools)</summary>

| Tool | What it does |
| --- | --- |
| `graphql_query` | Run any raw GraphQL query against Ensembl |
| `graphql_query_to_file` | Run a raw query and save the JSON result to a file |
| `get_variant_to_file` | Write a full variant annotation to a JSON file |

</details>

Most tools default to the human reference genome
(`a7335667-93e7-11ec-a39d-005056b38ce3`). Use `find_genomes` for other species.

---

<details>
<summary><strong>Development</strong></summary>

### From source

```bash
git clone https://github.com/ensembl-mcp/ensembl-mcp.git  # or your fork
cd ensembl-mcp
uv sync          # install dependencies
uv sync --dev    # include agent/test dependencies
```

Requires Python 3.14+.

### Run tests

Integration tests hit the live Ensembl endpoint and skip gracefully when offline:

```bash
uv run pytest                        # all tests
uv run pytest -m integration         # integration only
uv run pytest tests/test_enriched_tools.py -v  # new tool tests
```

The Agno natural-language agent tests also require `ENSEMBL_MCP_AGENT_API_KEY`
(an OpenRouter key); without it, those tests are skipped.

### CLI reference

See [CLI Reference](docs/cli_reference.md) for all available commands and
natural-language agent examples.

</details>

---

## Detailed Documentation

| Document | What's inside |
| --- | --- |
| [Client Setup](docs/client_setup.md) | Copy-paste configs for Claude, Codex, Antigravity, Cursor, and Cline |
| [Configuration](docs/configuration.md) | All `ENSEMBL_MCP_*` environment variables |
| [CLI Reference](docs/cli_reference.md) | `serve`, `examples`, and `agent` commands |
| [Variant Contract](docs/variant_contract.md) | Variant annotation structure, prediction scoping, clinical summary |
| [Validation](docs/validation.md) | Why LLMs need ground-truth genomic data, failure modes |
| [Ensembl Beta Backends](docs/ensembl_beta_backends.md) | Multi-backend architecture map |
| [Architecture & Refget](docs/refget_and_architecture.md) | Modular client design, GA4GH Refget integration |
