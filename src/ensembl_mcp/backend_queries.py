"""Queries for Ensembl beta backends outside the core GraphQL schema."""

VARIATION_VERSION_QUERY = """
query {
  version {
    api { major minor patch }
  }
}
"""

PREDICTION_FIELDS = """
    score
    result
    classification { accession_id value }
    analysis_method {
      tool
      version
      qualifier { result_type modes }
    }
"""

COMPACT_VARIANT_FIELDS = f"""
    name
    alternative_names {{ accession_id name description url }}
    type
    allele_type {{ accession_id value }}
    primary_source {{ accession_id name description url }}
    slice {{
      region {{ name }}
      location {{ start end length }}
      strand {{ code value }}
    }}
    prediction_results {{ {PREDICTION_FIELDS} }}
    alleles {{
      name
      allele_sequence
      reference_sequence
      allele_type {{ accession_id value }}
      population_frequencies {{
        population_name
        allele_frequency
        allele_count
        allele_number
        is_minor_allele
        is_hpmaf
      }}
      prediction_results {{ {PREDICTION_FIELDS} }}
      ensembl_website_display_data {{
        count_transcript_consequences
        count_overlapped_genes
        count_regulatory_consequences
        count_variant_phenotypes
        count_gene_phenotypes
        representative_population_allele_frequency
      }}
    }}
    ensembl_website_display_data {{ count_citations }}
"""

FULL_VARIANT_FIELDS = f"""
    {COMPACT_VARIANT_FIELDS}
    alleles {{
      name
      phenotype_assertions {{
        feature
        feature_type {{ accession_id value }}
        phenotype {{
          name
          source {{ id name description url release }}
          ontology_terms {{ accession_id name description url }}
        }}
        evidence {{
          source {{ id name description url release }}
          assertion {{
            label
            definition
            description
            ... on ValueSet {{ accession_id value is_current }}
          }}
        }}
      }}
      predicted_molecular_consequences {{
        allele_name
        stable_id
        feature_type {{ accession_id value }}
        consequences {{ accession_id value }}
        gene_stable_id
        gene_symbol
        protein_stable_id
        transcript_biotype
        cdna_location {{ start end length }}
        cds_location {{ start end length }}
        protein_location {{ start end length }}
        prediction_results {{ {PREDICTION_FIELDS} }}
      }}
    }}
"""

VARIANT_QUERY = f"""
query VariantById($genome_id: String!, $variant_id: String!) {{
  variant(by_id: {{ genome_id: $genome_id, variant_id: $variant_id }}) {{
    {FULL_VARIANT_FIELDS}
  }}
}}
"""

COMPACT_VARIANT_QUERY = f"""
query VariantById($genome_id: String!, $variant_id: String!) {{
  variant(by_id: {{ genome_id: $genome_id, variant_id: $variant_id }}) {{
    {COMPACT_VARIANT_FIELDS}
  }}
}}
"""

POPULATIONS_QUERY = """
query Populations($genome_id: String!) {
  populations(genome_id: $genome_id) {
    name
    description
    type
    is_global
    display_group_name
    super_population { name }
    sub_populations { name }
  }
}
"""

HOMOLOGIES_QUERY = """
query Homologies($genome_id: String!, $gene_stable_id: String!) {
  homologies(genome_id: $genome_id, gene_stable_id: $gene_stable_id) {
    type
    subtype { accession_id label value definition }
    query_genome {
      genome_id
      common_name
      scientific_name
      assembly { accession_id name }
    }
    query_gene { stable_id symbol version unversioned_stable_id }
    target_genome {
      genome_id
      common_name
      scientific_name
      assembly { accession_id name }
    }
    target_gene { stable_id symbol version unversioned_stable_id }
    stats {
      query_percent_id
      query_percent_coverage
      target_percent_id
      target_percent_coverage
    }
  }
}
"""
