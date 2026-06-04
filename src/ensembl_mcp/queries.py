"""GraphQL query strings for the Ensembl beta core schema.

Field selections below were verified against the live endpoint
(``https://beta.ensembl.org/data/graphql/core``).
"""

SLICE_FRAGMENT = """
    slice {
      region { name length code topology }
      location { start end length }
      strand { code value }
    }
"""

GENE_FIELDS = f"""
    stable_id
    unversioned_stable_id
    symbol
    name
    so_term
    version
    transcript_count
    {SLICE_FRAGMENT}
"""

TRANSCRIPT_FIELDS = f"""
    stable_id
    unversioned_stable_id
    symbol
    so_term
    version
    {SLICE_FRAGMENT}
"""

PRODUCT_FIELDS = """
    stable_id
    unversioned_stable_id
    type
    length
    version
"""

GENOME_FIELDS = """
    genome_id
    assembly_accession
    scientific_name
    release_number
    release_date
    taxon_id
    parlance_name
    genome_tag
    is_reference
"""

REGION_FIELDS = """
    name
    length
    code
    topology
"""

VERSION_QUERY = """
query {
  version {
    api { major minor patch }
  }
}
"""

GENES_BY_SYMBOL_QUERY = f"""
query GenesBySymbol($symbol: String!, $genome_id: String!) {{
  genes(by_symbol: {{ symbol: $symbol, genome_id: $genome_id }}) {{
    {GENE_FIELDS}
  }}
}}
"""

GENE_BY_ID_QUERY = f"""
query GeneById($genome_id: String!, $stable_id: String!) {{
  gene(by_id: {{ genome_id: $genome_id, stable_id: $stable_id }}) {{
    {GENE_FIELDS}
  }}
}}
"""

TRANSCRIPT_BY_ID_QUERY = f"""
query TranscriptById($genome_id: String!, $stable_id: String!) {{
  transcript(by_id: {{ genome_id: $genome_id, stable_id: $stable_id }}) {{
    {TRANSCRIPT_FIELDS}
  }}
}}
"""

TRANSCRIPT_BY_SYMBOL_QUERY = f"""
query TranscriptBySymbol($genome_id: String!, $symbol: String!) {{
  transcript(by_symbol: {{ genome_id: $genome_id, symbol: $symbol }}) {{
    {TRANSCRIPT_FIELDS}
  }}
}}
"""

TRANSCRIPT_SEARCH_QUERY = f"""
query TranscriptSearch($payload: TranscriptsSearchInput!) {{
  transcript_search(search_payload: $payload) {{
    meta {{ total_hits page per_page }}
    matches {{
      {TRANSCRIPT_FIELDS}
    }}
  }}
}}
"""

PRODUCT_BY_ID_QUERY = f"""
query ProductById($genome_id: String!, $stable_id: String!) {{
  product(by_id: {{ genome_id: $genome_id, stable_id: $stable_id }}) {{
    {PRODUCT_FIELDS}
  }}
}}
"""

REGION_BY_NAME_QUERY = f"""
query RegionByName($genome_id: String!, $name: String!) {{
  region(by_name: {{ genome_id: $genome_id, name: $name }}) {{
    {REGION_FIELDS}
  }}
}}
"""

OVERLAP_REGION_QUERY = f"""
query OverlapRegion($genome_id: String!, $region_name: String!, $start: Int!, $end: Int!) {{
  overlap_region(by_slice: {{
    genome_id: $genome_id,
    region_name: $region_name,
    start: $start,
    end: $end
  }}) {{
    genes {{ {GENE_FIELDS} }}
    transcripts {{ {TRANSCRIPT_FIELDS} }}
  }}
}}
"""

GENOMES_BY_KEYWORD_QUERY = f"""
query GenomesByKeyword($keyword: GenomeBySpecificKeywordInput!) {{
  genomes(by_keyword: $keyword) {{
    {GENOME_FIELDS}
  }}
}}
"""

GENOME_BY_ID_QUERY = f"""
query GenomeById($genome_id: String!) {{
  genome(by_genome_id: {{ genome_id: $genome_id }}) {{
    {GENOME_FIELDS}
  }}
}}
"""
