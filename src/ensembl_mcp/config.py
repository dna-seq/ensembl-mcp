from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENDPOINT = "https://beta.ensembl.org/data/graphql/core"
DEFAULT_VARIATION_ENDPOINT = "https://beta.ensembl.org/api/graphql/variation"
DEFAULT_COMPARA_ENDPOINT = "https://beta.ensembl.org/api/graphql/compara"
DEFAULT_METADATA_ENDPOINT = "https://beta.ensembl.org/api/metadata"
DEFAULT_REST_ENDPOINT = "https://rest.ensembl.org"

HUMAN_GENOME_ID = "a7335667-93e7-11ec-a39d-005056b38ce3"

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the Ensembl GraphQL MCP server.

    Values can be overridden via ``ENSEMBL_MCP_*`` environment variables or a
    local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="ENSEMBL_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    endpoint: str = Field(
        default=DEFAULT_ENDPOINT,
        description="Base Ensembl GraphQL endpoint used for all queries.",
    )
    refget_endpoint: str = Field(
        default="https://beta.ensembl.org/data/refget",
        description="Base Ensembl Refget endpoint used for sequence queries.",
    )
    variation_endpoint: str = Field(
        default=DEFAULT_VARIATION_ENDPOINT,
        description="Ensembl beta variation GraphQL endpoint.",
    )
    compara_endpoint: str = Field(
        default=DEFAULT_COMPARA_ENDPOINT,
        description="Ensembl beta compara GraphQL endpoint.",
    )
    metadata_endpoint: str = Field(
        default=DEFAULT_METADATA_ENDPOINT,
        description="Base Ensembl beta metadata REST endpoint.",
    )
    rest_endpoint: str = Field(
        default=DEFAULT_REST_ENDPOINT,
        description="Base legacy Ensembl REST endpoint used to resolve rsIDs.",
    )
    request_timeout: float = Field(
        default=60.0,
        description=(
            "HTTP timeout in seconds. Kept generous because some Ensembl beta "
            "queries (e.g. genome keyword search) can be slow."
        ),
    )
    human_genome_id: str = Field(
        default=HUMAN_GENOME_ID,
        description="Genome id for the human reference assembly (GRCh38).",
    )
    output_dir: str = Field(
        default=".ensembl_mcp_outputs",
        description="Directory for tools that write large results to files.",
    )
    agent_api_key: str | None = Field(
        default=None,
        description="API key used by the optional Agno natural-language agent.",
    )
    agent_model_id: str = Field(
        default="z-ai/glm-5.2",
        description="OpenAI-compatible model id used by the optional Agno agent.",
    )
    agent_base_url: str | None = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenAI-compatible base URL for the Agno agent model.",
    )
    agent_timeout: float = Field(
        default=120.0,
        description="HTTP timeout in seconds for Agno model calls.",
    )


def get_settings() -> Settings:
    return Settings()
